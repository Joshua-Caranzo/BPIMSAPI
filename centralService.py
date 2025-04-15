from tortoise import Tortoise
from utils import create_response
import transactionService
from models import User, CartItems, Item, Customer, Cart, BranchItem, Branch, Transaction, TransactionItem
from decimal import Decimal
from datetime import datetime, time, timedelta, timezone

async def getCentralProducts(categoryId, page=1, search=""):
    pageSize = 30
    offset = (page - 1) * pageSize

    sqlQuery = """
        SELECT 
            i.id, 
            i.name, 
            i.categoryId, 
            i.price, 
            i.cost, 
            i.isManaged, 
            i.imagePath, 
            i.sellByUnit,
            i.storeCriticalValue,
            c.name as categoryName,
            i.whCriticalValue,
            i.unitOfMeasure
        FROM items i
        LEFT JOIN categories c on c.Id = i.categoryId
        WHERE i.isManaged = 1
    """

    params = []

    if categoryId != 0 and categoryId != -1:
        sqlQuery += " AND i.categoryId = %s"
        params.append(categoryId)

    if search:
        sqlQuery += " AND i.name LIKE %s"
        params.append(f'%{search}%')
    sqlQuery += " ORDER BY i.name"
    sqlQuery += " LIMIT %s OFFSET %s"
    params.extend([pageSize, offset])

    connection = Tortoise.get_connection('default')
    result = await connection.execute_query(sqlQuery, tuple(params))

    countQuery = """
        SELECT COUNT(*) 
        FROM items i
        WHERE i.isManaged = 1
    """
    totalCountResult = await connection.execute_query(countQuery)
    totalCount = totalCountResult[1][0]['COUNT(*)']

    items = result[1]

    for item in items:
        item['branchProducts'] = await getBranchProducts(item['id'])

    itemList = [
        {
            "id": item['id'],
            "name": item['name'],
            "categoryId": item['categoryId'],
            "price": item['price'],
            "cost": item['cost'],
            "isManaged": item['isManaged'],
            "imagePath": item['imagePath'],
            "sellByUnit": bool(item['sellByUnit']),
            "storeCriticalValue": item['storeCriticalValue'],
            "categoryName":item['categoryName'],
            "whCriticalValue":item['whCriticalValue'],
            "unitOfMeasure":item['unitOfMeasure'],
            "branchProducts":item['branchProducts']
        }
        for item in items
    ]

    return create_response(True, 'Items Successfully Retrieved', itemList, None, totalCount), 200

async def getBranchProducts(itemId):

    sqlQuery = """
        SELECT bi.id, bi.branchId, b.name as branchName, bi.quantity
        From branchitem bi inner join branches b on b.Id = bi.branchId 
        where bi.itemId = %s and b.isActive = 1
    """

    params = [itemId]

    sqlQuery += " ORDER BY b.id"

    connection = Tortoise.get_connection('default')
    result = await connection.execute_query(sqlQuery, tuple(params))

    items = result[1]

    itemList = [
        {
            "id": item['id'],
            "branchId": item['branchId'],
            "branchName": item['branchName'],
            "quantity": item['quantity']
        }
        for item in items
    ]

    return itemList

async def getCentralCartandItems(userId):
    cart = await transactionService.getCartforUser(userId)
    user = await User.get_or_none(id = userId)
    totalCount = await transactionService.getTotalItemCount(cart.id);    
    cartItems = await getCentralCartItems(cart.id)

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

async def getCentralCartItems(cartId):
    cartItems = await CartItems.all().filter(cartId=cartId)
    result = []

    if cartItems:
        for cartItem in cartItems:
            branchItem = await BranchItem.get_or_none(id = cartItem.branchItemId)
            item = await Item.get_or_none(id=branchItem.itemId)

            if item:
                result.append({
                    "id": cartItem.id,
                    "itemId": item.id,
                    "name": item.name,
                    "price": item.price,
                    "quantity": cartItem.quantity,
                    "sellByUnit": item.sellByUnit
                })

    return result

from decimal import Decimal, InvalidOperation

async def addCentralItemToCart(cartId, branchProducts):
    message = None

    for bp in branchProducts:
        sold_qty = bp.get('soldQuantity')

        if not sold_qty:
            continue

        try:
            quantity_decimal = Decimal(sold_qty)
        except InvalidOperation:
            continue  

        if quantity_decimal <= 0:
            continue

        branchItem = await BranchItem.get_or_none(id=bp['id'])
        if not branchItem:
            continue

        item = await Item.get_or_none(id=branchItem.itemId)
        if branchItem.quantity < quantity_decimal:
            return create_response(False, 'Not enough stock available for this item', None, None), 200

        existing_cart_item = await CartItems.get_or_none(cartId=cartId, branchItemId=branchItem.id)

        if existing_cart_item:
            existing_cart_item.quantity += quantity_decimal
            await existing_cart_item.save()
            message = 'Item quantity updated in the cart'
        else:
            await CartItems.create(cartId=cartId, branchItemId=branchItem.id, quantity=quantity_decimal)
            message = 'Item successfully added to the cart' 

        cart = await Cart.get_or_none(id=cartId)
        cart.subTotal += item.price * quantity_decimal
        await cart.save()    
    
    return create_response(True, message or "No items added to cart", None, None), 200

async def processCentralPayment(cartId, amountReceived, isCredit):
    cart = await Cart.get_or_none(id=cartId)

    if not cart:
        return create_response(False, 'Transaction Error. Please Try Again!'), 404
    
    user = await User.get_or_none(id=cart.userId)
    branch = await Branch.get_or_none(id=1)
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

    slip_no = await transactionService.generate_slip_no(branch.id)
    total_profit = 0 

    total_cogs = 0
    for cItem in cartItems:
        branchItem = await BranchItem.get_or_none(id=cItem.branchItemId)
        item = await Item.get_or_none(id=branchItem.itemId)
        if item:
            total_cogs += item.cost * cItem.quantity  

    total_profit = total_amount - total_cogs
    current_time = datetime.now(timezone.utc) + timedelta(hours=8)
    adjusted_time = transactionService.adjust_transaction_time(current_time)

    transaction = await Transaction.create(
        amountReceived=float(amountReceived),
        totalAmount=total_amount,
        cashierId=cart.userId,
        slipNo=slip_no,
        transactionDate = adjusted_time,
        branchId=1,
        profit=total_profit,
        discount=cart.discount,
        deliveryFee=cart.deliveryFee,
        isExacon = True,
        isPaid = False if isCredit else True
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
            "customerName": customer.name if customer else None,
            "isCredit": isCredit
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

async def getAllCentralTransactionsAsync(categoryId,page=1, search=""):
    pageSize = 30
    offset = (page - 1) * pageSize

    params = [categoryId]

    dailyTransactsDto = """
        SELECT tr.id, tr.totalAmount, tr.slipNo, tr.transactionDate, u.name as cashierName, tr.isVoided, tr.isPaid
        FROM transactions tr
        INNER JOIN users u ON u.id = tr.cashierId
        WHERE tr.isExacon = 1 AND (%s = 0 OR tr.isPaid = 0)
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
            "isPaid": bool(tr["isPaid"]),
            "items": items
        })

    transactions = transactionsDto
    total_count_query = "SELECT COUNT(*) as total FROM transactions WHERE isExacon = 1"
    total_count_result = await Tortoise.get_connection("default").execute_query_dict(total_count_query)  # Exclude LIMIT & OFFSET params
    total_count = total_count_result[0]["total"] if total_count_result else 0

    return create_response(True, "Successfully Retrieved", transactions, None, total_count), 200

async def payPendingTransaction(transactionId, amount):
    transaction = await Transaction.get_or_none(id = transactionId)
    transaction.isPaid = True
    transaction.amountReceived = amount
    
    await transaction.save()
    
    return create_response(True, "Successfully Paid", None, None), 200