from models import Item, Cart, CartItems, Transaction, TransactionItem,User, Branch, Customer, BranchItem
from utils import create_response
from datetime import datetime, time
from decimal import Decimal
from tortoise import Tortoise
import pytz

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
        JOIN items i ON ci.itemId = i.id
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
            item = await Item.get_or_none(id=cartItem.itemId)
            branchItem = await BranchItem.get_or_none(itemId=cartItem.itemId, branchId = branchId)
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

from decimal import Decimal

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

    existing_cart_item = await CartItems.get_or_none(cartId=cart.id, itemId=item.id)

    if existing_cart_item:
        existing_cart_item.quantity += quantity_decimal
        await existing_cart_item.save()
        message = 'Item quantity updated in the cart'
    else:
        await CartItems.create(cartId=cart.id, itemId=item.id, quantity=quantity_decimal)
        message = 'Item successfully added to the cart'

    cart.subTotal += item.price * quantity_decimal
    await cart.save()

    await branch_item.save()

    return create_response(True, message, None, None), 200


async def updateItemQuantity(cartItemId, quantity):
    cartItem = await CartItems.get_or_none(id = cartItemId)
    item = await Item.get_or_none(id = cartItem.itemId)
    cart = await Cart.get_or_none(id=cartItem.cartId)
    quantity_decimal = Decimal(str(quantity))
    user = await User.get_or_none(id = cart.userId)
    branchItem = await BranchItem.get_or_none(branchId = user.branchId, itemId = item.id)

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

    if cartItem:
        item = await Item.get_or_none(id=cartItem.itemId)
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

async def processPayment(cartId, amountReceived):
    cart = await Cart.get_or_none(id=cartId)

    if not cart:
        return create_response(False, 'Transaction Error. Please Try Again!'), 404
    
    user = await User.get_or_none(id=cart.userId)
    branch = await Branch.get_or_none(id=user.branchId)
    customer = await Customer.get_or_none(id=cart.customerId) if cart.customerId else None
    cartItems = await CartItems.filter(cartId=cartId)
    transactionItems = []

    # Calculate total amount (revenue)
    total_amount = cart.subTotal
    if cart.discount:
        total_amount -= cart.discount  # Discount reduces revenue
    if cart.deliveryFee:
        total_amount += cart.deliveryFee  # Delivery fee increases revenue

    if total_amount > float(amountReceived):
        return create_response(False, 'Transaction Error. Please Try Again!'), 404

    slip_no = await generate_slip_no(cart.userId)
    total_profit = 0 

    # Calculate total cost of goods sold (COGS)
    total_cogs = 0
    for cItem in cartItems:
        item = await Item.get_or_none(id=cItem.itemId)
        if item:
            total_cogs += item.cost * cItem.quantity  # Sum up COGS

    # Calculate profit: Revenue - COGS - Discounts + Delivery Fees
    total_profit = total_amount - total_cogs

    transaction = await Transaction.create(
        amountReceived=float(amountReceived),
        totalAmount=total_amount,
        cashierId=cart.userId,
        slipNo=slip_no,
        transactionDate = datetime.now(pytz.utc).astimezone(sgt),
        customerId=cart.customerId,
        branchId=user.branchId,
        profit=total_profit,  # Updated profit calculation
        discount=cart.discount,
        deliveryFee=cart.deliveryFee
    )

    for cItem in cartItems:
        item = await Item.get_or_none(id=cItem.itemId)
        if item:    
            branchItem = await BranchItem.get_or_none(branchId=user.branchId, itemId=item.id)
            branchItem.quantity -= cItem.quantity
            itemAmount = item.price * cItem.quantity

            tItem = await TransactionItem.create(
                transactionId=transaction.id,
                itemId=cItem.itemId,
                quantity=cItem.quantity,
                amount=itemAmount
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
        "transactionItems": transactionItems
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

async def generate_slip_no(cashierId: int) -> str:
    now_sg = datetime.now(pytz.utc).astimezone(sgt)
    
    dateToday = now_sg.strftime('%m%d%y')
    store_code = f"{cashierId:02d}"
    
    today_date = now_sg.date()

    start_of_day = sgt.localize(datetime.combine(today_date, time.min))
    end_of_day = sgt.localize(datetime.combine(today_date, time.max))

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
                "sellByUnit": bool(item.sellByUnit)
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
            "customerName": customer.name if customer else None
        },
        "transactionItems": items
    }
    
    return create_response(True, 'Transaction retrieved successfully', transactionData), 200
