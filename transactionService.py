from models import Item, Cart, CartItems, Transaction, TransactionItem,User, Branch, Customer, BranchItem, LoyaltyStages, ItemReward,LoyaltyCustomer
from utils import create_response
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
from tortoise import Tortoise
import pytz
import customerService

sgt = pytz.timezone('Asia/Singapore')

""" GET METHODS """
async def getCartandItems(userId):
    cart = await getCartforUser(userId)
    user = await User.get_or_none(id = userId)
    totalCount = await getTotalItemCount(cart.id);    
    cartItems = await getCartItems(cart.id, user.branchId)

    cart_data = cart.__dict__  
    cart_data.pop('userId', None)
    customer = None
    if(cart_data["customerId"]):
        customer = await Customer.get_or_none(id = cart_data["customerId"])

    cartDto = {
            "cart": {
                "id": cart_data["id"],
                "discount": cart_data["discount"],
                "deliveryFee": cart_data["deliveryFee"],
                "subTotal": str(cart_data["subTotal"]),
                "customerName": customer.name if customer else None 
            },
            "cartItems": cartItems
        }

    return create_response(True, "Successfully retrieved cart and items", cartDto, None, totalCount), 200


async def getTotalItemCount(cartId):
    query = """
        SELECT SUM(CASE 
                    WHEN i.sellbyUnit = 1 THEN ci.quantity 
                    ELSE 1 
                   END) AS total_count
        FROM cartitems ci
        INNER JOIN branchItem bi ON ci.branchItemId = bi.id
        INNER JOIN items i on i.id = bi.itemId
        WHERE ci.cartId = %s
    """
    result = await Tortoise.get_connection("default").execute_query(query, [cartId])
    return int(result[1][0]["total_count"]) if result[1][0]["total_count"] else 0


async def getCartforUser(userId):
    cart = await Cart.get_or_none(userId=userId)
    
    if not cart:
        cart = await createCartforUser(userId)
    
    return cart


async def getCartItems(cartId, branchId):
    cartItems = await CartItems.all().filter(cartId=cartId)
    result = []

    if cartItems:
        for cartItem in cartItems:
            branchItem = await BranchItem.get_or_none(id=cartItem.branchItemId)
            item = await Item.get_or_none(id=branchItem.itemId)
            if item:
                result.append({
                    "id": cartItem.id,
                    "itemId": item.id,
                    "name": item.name,
                    "price": item.price,
                    "quantity": cartItem.quantity,
                    "sellByUnit": item.sellByUnit,
                    "branchQty": branchItem.quantity
                })

    return result


"""POST AND PUT METHODS"""

async def createCartforUser(userId):
    cart = await Cart.get_or_none(userId=userId)

    if cart:
        return cart
    
    cart = await Cart.create(userId=userId, subTotal=0.00) 

    return cart


async def deleteAllCartItems(cartId):
    cartItems = await CartItems.all().filter(cartId=cartId)
    cart = await Cart.get_or_none(id=cartId)
    user = await User.get_or_none(id = cart.userId)

    if cartItems:
        for cartItem in cartItems:
            await cartItem.delete()

        message = 'Cart items deleted successfully'
        
        cart.subTotal = 0.00
        cart.discount = None
        cart.deliveryFee = None
        cart.customerId = None
        await cart.save()
        
    else:
        message = 'No items in the cart'

    return create_response(True, message), 200


async def addItemToCart(cartId, itemId, quantity):
    item = await Item.get_or_none(id=itemId)
    quantity_decimal = Decimal(str(quantity))

    if not item:
        return create_response(False, 'Item not found', None, None), 200

    cart = await Cart.get_or_none(id=cartId)
    if not cart:
        return create_response(False, 'Cart not found', None, None), 200

    user = await User.get_or_none(id=cart.userId)
    branch_item = await BranchItem.get_or_none(itemId=itemId, branchId=user.branchId)

    if not branch_item or branch_item.quantity < quantity_decimal:
        return create_response(False, 'Not enough stock available for this item', None, None), 200

    existing_cart_item = await CartItems.get_or_none(cartId=cart.id, branchItemId=branch_item.id)

    if existing_cart_item:
        existing_cart_item.quantity += quantity_decimal
        await existing_cart_item.save()
        message = 'Item quantity updated in the cart'
    else:
        await CartItems.create(cartId=cart.id, branchItemId=branch_item.id, quantity=quantity_decimal)
        message = 'Item successfully added to the cart' 

    cart = await Cart.get_or_none(id=cartId)
    cart.subTotal += item.price * quantity_decimal
    await cart.save()       
    return create_response(True, message, None, None), 200

async def updateItemQuantity(cartItemId, quantity):
    cartItem = await CartItems.get_or_none(id = cartItemId)
    cart = await Cart.get_or_none(id=cartItem.cartId)
    quantity_decimal = Decimal(str(quantity))
    user = await User.get_or_none(id = cart.userId)
    branchItem = await BranchItem.get_or_none(id = cartItem.branchItemId)
    item = await Item.get_or_none(id = branchItem.itemId)

    if cartItem:
        totalToAdd = (item.price * quantity_decimal) - (cartItem.quantity * item.price)
        cartItem.quantity = quantity_decimal
        cart.subTotal += totalToAdd
        await cartItem.save()
        await cart.save()
        await branchItem.save()
        message = 'Item quantity and price updated'
    else:
        message = 'No item found in the cart'

    return create_response(True, message), 200

async def removeCartItem(cartItemId):
    cartItem = await CartItems.get_or_none(id=cartItemId)
    cart = await Cart.get_or_none(id=cartItem.cartId)
    user = await User.get_or_none(id = cart.userId)
    branchItem = await BranchItem.get_or_none(id = cartItem.branchItemId)
    if cartItem:
        item = await Item.get_or_none(id=branchItem.itemId)
        cart = await Cart.get_or_none(id=cartItem.cartId)
        
        if cart and item:
            cart.subTotal -= item.price * cartItem.quantity
            if cart.subTotal < 0:
                cart.subTotal = 0
                cart.deliveryFee = 0
                cart.discount = 0

            await cart.save()
            await cartItem.delete()

            message = 'Item removed from the cart successfully'
        else:
            message = 'Cart or item not found'
    else:
        message = 'No item found in the cart'

    return create_response(True, message), 200


async def updateDeliveryFee(cartId, deliveryFee):
    cart = await Cart.get_or_none(id=cartId)

    if cart:
        cart.deliveryFee = deliveryFee
        await cart.save()

        message = 'Successful'
    else:
        message = 'Cart not Found'

    return create_response(True, message), 200


async def updateDiscount(cartId, discount):
    cart = await Cart.get_or_none(id=cartId)

    if(discount and discount > cart.subTotal):
        return create_response(False, 'Updating Discount Error. Please Try Again!'), 200
    
    if cart:
        cart.discount = discount
        await cart.save()

        message = 'Successful'
    else:
        message = 'Cart not Found'

    return create_response(True, message), 200

async def updateCustomer(cartId, custId):
    cart = await Cart.get_or_none(id=cartId)
    
    if cart:
        cart.customerId = custId
        await cart.save()

        message = 'Successful'
    else:
        message = 'Cart not Found'

    return create_response(True, message), 200

def adjust_transaction_time(transaction_dt):
    """Adjusts the transaction time to 5 PM if it's after 5 PM and before 7 AM if earlier."""
    transaction_time = transaction_dt.time()

    if transaction_time >= time(17, 0):  
        transaction_dt = transaction_dt.replace(hour=17, minute=0, second=0, microsecond=0)
    elif transaction_time < time(7, 0): 
        transaction_dt = transaction_dt.replace(hour=7, minute=0, second=0, microsecond=0)

    return transaction_dt

async def processPayment(cartId, amountReceived):
    cart = await Cart.get_or_none(id=cartId)

    if not cart:
        return create_response(False, 'Transaction Error. Please Try Again!'), 404
    
    user = await User.get_or_none(id=cart.userId)
    branch = await Branch.get_or_none(id=user.branchId)
    customer = await Customer.get_or_none(id=cart.customerId) if cart.customerId else None
    cartItems = await CartItems.filter(cartId=cartId)
    transactionItems = []

    total_amount = cart.subTotal
    if cart.discount:
        total_amount -= cart.discount  
    if cart.deliveryFee:
        total_amount += cart.deliveryFee  

    if total_amount > float(amountReceived):
        return create_response(False, 'Transaction Error. Please Try Again!'), 404

    slip_no = await generate_slip_no(branch.id)
    total_profit = 0 

    total_cogs = 0
    for cItem in cartItems:
        branchItem = await BranchItem.get_or_none(id=cItem.branchItemId)
        item = await Item.get_or_none(id=branchItem.itemId)
        if item:
            total_cogs += item.cost * cItem.quantity  

    total_profit = total_amount - total_cogs
    current_time = datetime.now(timezone.utc) + timedelta(hours=8)
    adjusted_time = adjust_transaction_time(current_time)

    transaction = await Transaction.create(
        amountReceived=float(amountReceived),
        totalAmount=total_amount,
        cashierId=cart.userId,
        slipNo=slip_no,
        transactionDate = adjusted_time,
        customerId=cart.customerId,
        branchId=user.branchId,
        profit=total_profit,
        discount=cart.discount,
        deliveryFee=cart.deliveryFee
    )

    for cItem in cartItems:
        branchItem = await BranchItem.get_or_none(id=cItem.branchItemId)
        item = await Item.get_or_none(id=branchItem.itemId)
        if item:    
            branchItem.quantity -= cItem.quantity
            itemAmount = item.price * cItem.quantity

            tItem = await TransactionItem.create(
                transactionId=transaction.id,
                itemId=branchItem.itemId,
                quantity=cItem.quantity,
                amount=itemAmount,
                isVoided=False
            )
            transactionItems.append({
                "id": tItem.id,
                "itemId": item.id,
                "name": item.name,
                "price": item.price,
                "quantity": tItem.quantity,
                "amount": tItem.amount,
                "sellByUnit": item.sellByUnit
            })

    await branchItem.save()

    loyaltyItem = {}
    done = False
    if total_amount >= 3000 and customer:
        loyaltyItem["newProgress"] = True
        customerStages = await LoyaltyCustomer.filter(customerId=customer.id)
        if customerStages:
            done = await customerService.markNextStageDone(customer.id)
        else:
            await customerService.saveLoyaltyCustomer(customer.id)
            customer.isLoyalty = True

        query = """
            SELECT ls.orderId, ls.itemRewardId, lc.id as lcId
            FROM loyaltycustomers lc
            JOIN loyaltyStages ls ON lc.stageId = ls.id
            WHERE lc.customerId = %s AND lc.isDone = TRUE
            ORDER BY ls.orderId DESC
            LIMIT 1
        """
        
        latest_stage = await Tortoise.get_connection("default").execute_query_dict(query, [customer.id])
        if latest_stage:
            latest_stage = latest_stage[0]  
            loyaltyItem["currentStage"] = latest_stage["orderId"]
            loyaltyItem["id"] = latest_stage["lcId"]
            loyaltyItem["completeLoyalty"] = done

            if latest_stage["itemRewardId"] is not None:
                rewardItem = await ItemReward.get_or_none(id=latest_stage["itemRewardId"])
                if rewardItem:
                    loyaltyItem["hasReward"] = True
                    loyaltyItem["rewardName"] = rewardItem.name
                    loyaltyItem['isItem'] = True if rewardItem.id == 1 else False

    transactionRequest = {
        "transaction": {
            "id": transaction.id,
            "totalAmount": transaction.totalAmount,
            "amountReceived": transaction.amountReceived,
            "slipNo": transaction.slipNo,
            "transactionDate": transaction.transactionDate,
            "branch": branch.name,
            "deliveryFee": cart.deliveryFee,
            "discount": cart.discount,
            "subTotal": cart.subTotal,
            "customerName": customer.name if customer else None
        },
        "transactionItems": transactionItems,
        "loyaltyItemDto": loyaltyItem
    }

    await CartItems.filter(cartId=cartId).delete()
    cart.subTotal = 0
    cart.deliveryFee = None
    cart.discount = None
    cart.customerId = None
    await cart.save()

    if customer:
        customer.totalOrderAmount += total_amount
        await customer.save()

    message = 'Payment Successful'
    return create_response(True, message, transactionRequest), 200

async def generate_slip_no(branchId: int) -> str:
    now_sg = datetime.now(timezone.utc) + timedelta(hours=8)
    
    dateToday = now_sg.strftime('%m%d%y')
    store_code = f"{branchId:02d}"
    today_date = now_sg.date()

    start_of_day = datetime.combine(today_date, time.min, timezone.utc) + timedelta(hours=8)
    end_of_day = datetime.combine(today_date, time.max, timezone.utc) + timedelta(hours=8)

    transaction_count = await Transaction.filter(
        transactionDate__gte=start_of_day, 
        transactionDate__lte=end_of_day
    ).count()

    slip_count = transaction_count + 1
    slip_count_str = f"{slip_count:03d}"

    slip_no = f"CC{store_code}-{dateToday}-{slip_count_str}"

    return slip_no

async def getTransactionHistory(transactionId):
    transaction = await Transaction.get_or_none(id=transactionId)
    
    if not transaction:
        return create_response(False, 'Transaction not found!'), 404
    
    branch = await Branch.get_or_none(id=transaction.branchId)
    customer = await Customer.get_or_none(id=transaction.customerId) if transaction.customerId else None
    transactionItems = await TransactionItem.filter(transactionId=transactionId)
    user = await User.get_or_none(id = transaction.cashierId)

    items = []
    for tItem in transactionItems:
        item = await Item.get_or_none(id=tItem.itemId)
        if item:
            items.append({
                "id": tItem.id,
                "itemId": item.id,
                "name": item.name,
                "price": item.price,
                "quantity": tItem.quantity,
                "amount": tItem.amount,
                "sellByUnit": item.sellByUnit
            })
    
    transactionData = {
        "transaction": {
            "id": transaction.id,
            "totalAmount": transaction.totalAmount,
            "amountReceived": transaction.amountReceived,
            "slipNo": transaction.slipNo,
            "transactionDate": transaction.transactionDate,
            "branch": branch.name if branch else None,
            "deliveryFee": transaction.deliveryFee,
            "discount": transaction.discount,
            "customerName": customer.name if customer else None,
            "cashier": user.name,
            "isVoided": bool(transaction.isVoided),
            "isPaid": bool(transaction.isPaid)
        },
        "transactionItems": items
    }
    
    return create_response(True, 'Transaction retrieved successfully', transactionData), 200

async def getAllTransactionsAsync(branchId, page=1, search=""):
    pageSize = 30
    offset = (page - 1) * pageSize

    params = [branchId]  

    dailyTransactsDto = """
        SELECT tr.id, tr.totalAmount, tr.slipNo, tr.transactionDate, u.name as cashierName, tr.isVoided
        FROM transactions tr
        INNER JOIN users u ON u.id = tr.cashierId
        WHERE tr.branchId = %s
    """
    
    if search:
        dailyTransactsDto += " AND tr.slipNo LIKE %s"
        params.append(f'%{search}%')
    dailyTransactsDto += " ORDER BY tr.transactionDate DESC"
    dailyTransactsDto += " LIMIT %s OFFSET %s"
    params.extend([pageSize, offset])

    dailyTransactions = await Tortoise.get_connection("default").execute_query_dict(dailyTransactsDto, tuple(params))

    transactionsDto = []

    for tr in dailyTransactions:
        itemsQuery = """
            SELECT ti.id, i.name as itemName, i.id as itemId, ti.quantity 
            FROM transactionitems ti
            INNER JOIN items i ON i.id = ti.itemId
            WHERE ti.transactionId = %s
        """
        items = await Tortoise.get_connection("default").execute_query_dict(itemsQuery, (tr['id'],))
        transactionsDto.append({
            "id": tr["id"],
            "totalAmount": float(tr["totalAmount"]),
            "slipNo": tr["slipNo"],
            "transactionDate": tr["transactionDate"],
            "cashierName": tr["cashierName"],
            "isVoided": bool(tr["isVoided"]),
            "items": items
        })

    transactions = transactionsDto
    total_count_query = "SELECT COUNT(*) as total FROM transactions WHERE branchId = %s"
    total_count_result = await Tortoise.get_connection("default").execute_query_dict(total_count_query, (branchId,))  # Exclude LIMIT & OFFSET params
    total_count = total_count_result[0]["total"] if total_count_result else 0

    return create_response(True, "Successfully Retrieved", transactions, None, total_count), 200

async def getAllTransactionsAsyncHQ(branchId=None, page=1, search=""):
    pageSize = 30
    offset = (page - 1) * pageSize
    params = []

    dailyTransactsDto = """
        SELECT tr.id, tr.totalAmount, tr.slipNo, tr.transactionDate, 
               u.name as cashierName, b.name as branchName, tr.isVoided
        FROM transactions tr
        INNER JOIN users u ON u.id = tr.cashierId
        INNER JOIN branches b ON b.id = tr.branchId
    """

    if branchId is not None:
        dailyTransactsDto += " WHERE tr.branchId = %s"
        params.append(branchId)

    if search:
        dailyTransactsDto += " AND" if branchId is not None else " WHERE"
        dailyTransactsDto += " tr.slipNo LIKE %s"
        params.append(f'%{search}%')

    dailyTransactsDto += " ORDER BY tr.transactionDate DESC"
    dailyTransactsDto += " LIMIT %s OFFSET %s"
    params.extend([pageSize, offset])

    dailyTransactions = await Tortoise.get_connection("default").execute_query_dict(dailyTransactsDto, tuple(params))

    transactionsDto = []

    for tr in dailyTransactions:
        itemsQuery = """
            SELECT ti.id, i.name as itemName, i.id as itemId, ti.quantity 
            FROM transactionitems ti
            INNER JOIN items i ON i.id = ti.itemId
            WHERE ti.transactionId = %s
        """
        items = await Tortoise.get_connection("default").execute_query_dict(itemsQuery, (tr['id'],))

        transactionsDto.append({
            "id": tr["id"],
            "totalAmount": float(tr["totalAmount"]),
            "slipNo": tr["slipNo"],
            "transactionDate": tr["transactionDate"],
            "cashierName": tr["cashierName"],
            "branchName": tr["branchName"],
            "isVoided": tr["isVoided"],
            "items": items
        })

    total_count_query = "SELECT COUNT(*) as total FROM transactions"
    count_params = []

    if branchId is not None:
        total_count_query += " WHERE branchId = %s"
        count_params.append(branchId)

    total_count_result = await Tortoise.get_connection("default").execute_query_dict(total_count_query, tuple(count_params))
    total_count = total_count_result[0]["total"] if total_count_result else 0

    return create_response(True, "Successfully Retrieved", transactionsDto, None, total_count), 200

async def voidTransaction(transactionId):
    transaction = await Transaction.get_or_none(id=transactionId)

    if not transaction:
        return create_response(False, 'Transaction not found!'), 404

    transactionItems = await TransactionItem.filter(transactionId=transactionId)
    customer = await Customer.get_or_none(id=transaction.customerId) if transaction.customerId else None

    transaction.isVoided = True
    await transaction.save()

    updatedBranchItems = []
    for tItem in transactionItems:
        branchItem = await BranchItem.get_or_none(branchId=transaction.branchId, itemId=tItem.itemId)
        if branchItem:
            branchItem.quantity += tItem.quantity
            await branchItem.save()
            updatedBranchItems.append({
                "itemId": tItem.itemId,
                "quantity": branchItem.quantity
            })

    if customer:
        customer.totalOrderAmount -= transaction.totalAmount
        await customer.save()

    return create_response(True, "Transaction voided successfully", None), 200

async def getOldestTransaction(branchId):
    if branchId != 0:
        transaction = await Transaction.filter(branchId=branchId).order_by('transactionDate').first()
    else:
        transaction = await Transaction.all().order_by('transactionDate').first()
    
    if not transaction:
        return create_response(False, 'Transaction not found!'), 404
    
    return create_response(True, 'Transaction retrieved successfully', transaction.transactionDate), 200
