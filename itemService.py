from models import BranchItem, StockInput, Item, Branch, WareHouseItem, CartItems
from utils import create_response, upload_media, delete_media
from tortoise import Tortoise
from decimal import Decimal

""" GET METHODS """
async def get_products(categoryId, branchId, page=1, search=""):
    pageSize = 30
    offset = (page - 1) * pageSize
    params = [branchId]

    if categoryId == -1:
        sqlQuery = """
            WITH HotItems AS (
                SELECT 
                    i.id, 
                    i.name, 
                    i.categoryId, 
                    i.price, 
                    i.cost, 
                    i.isManaged, 
                    i.imagePath, 
                    bi.quantity,
                    i.sellByUnit,
                    COUNT(ti.itemId) AS total_sales
                FROM transactionitems ti
                JOIN items i ON ti.itemId = i.id
                JOIN transactions tr ON ti.transactionId = tr.id
                JOIN branches b ON tr.branchId = b.id
                JOIN branchitem bi ON bi.itemId = i.id AND bi.branchId = b.id
                WHERE b.id = %s AND i.isManaged = 1
                GROUP BY i.id, i.name, i.categoryId, i.price, i.cost, i.isManaged, i.imagePath, bi.quantity, i.sellByUnit
            )
            SELECT * FROM HotItems 
            ORDER BY total_sales DESC 
            LIMIT %s OFFSET %s
        """
    else:
        sqlQuery = """
            SELECT 
                i.id, 
                i.name, 
                i.categoryId, 
                i.price, 
                i.cost, 
                i.isManaged, 
                i.imagePath, 
                bi.quantity,
                i.sellByUnit
            FROM items i
            LEFT JOIN branchitem bi ON i.id = bi.itemId
            WHERE bi.branchId = %s AND i.isManaged = 1
        """

        if categoryId != 0:
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
        LEFT JOIN branchitem bi ON i.id = bi.itemId
        WHERE bi.branchId = %s AND i.isManaged = 1
    """
    totalCountResult = await connection.execute_query(countQuery, (branchId,))
    totalCount = totalCountResult[1][0]['COUNT(*)']

    items = result[1]

    itemList = [
        {
            "id": item['id'],
            "name": item['name'],
            "categoryId": item['categoryId'],
            "price": item['price'],
            "cost": item['cost'],
            "isManaged": item['isManaged'],
            "imagePath": item['imagePath'],
            "quantity": item['quantity'],
            "sellByUnit": bool(item['sellByUnit'])
        }
        for item in items
    ]

    return create_response(True, 'Items Successfully Retrieved', itemList, None, totalCount), 200


async def getBranchStocks(categoryId, branchId, page=1, search=""):
    pageSize = 30
    offset = (page - 1) * pageSize

    sqlQuery = """
        SELECT bi.id, i.name, bi.quantity, i.unitOfMeasure, i.criticalValue, i.sellByUnit, i.moq, wi.quantity as whQuantity, i.imagePath FROM items i 
        INNER JOIN branchitem bi ON bi.itemId = i.id
        INNER JOIN warehouseitems wi ON wi.itemId = i.id
        WHERE bi.branchId = %s AND i.isManaged = 1
    """
    params = [branchId]

    if int(categoryId) == 1:
        sqlQuery += " AND bi.quantity < i.criticalValue"

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
        INNER JOIN branchitem bi ON bi.itemId = i.id
        INNER JOIN warehouseitems wi ON wi.itemId = i.id
        WHERE bi.branchId = %s AND i.isManaged = 1
    """
    totalCountResult = await connection.execute_query(countQuery, (branchId,))
    totalCount = totalCountResult[1][0]['COUNT(*)']

    items = result[1]

    itemList = [
        {
            "id": item['id'],
            "name": item['name'],
            "quantity": item['quantity'],
            "unitOfMeasure": item['unitOfMeasure'],
            "criticalValue": item['criticalValue'],
            "sellByUnit": bool(item['sellByUnit']),
            "moq": item['moq'],
            "imagePath": item['imagePath'],
            "whQty": item['whQuantity']
        }
        for item in items
    ]
    return create_response(True, 'Items Successfully Retrieved', itemList, None, totalCount), 200

async def getStockHistory(itemId):
    sqlQuery = """
        SELECT s.*, i.moq from stockinputs s inner join branchitem bi on s.branchItemId= bi.id
        INNER JOIN items i on i.id = bi.itemId WHERE s.branchItemId = %s
    """
    params = [itemId]

    sqlQuery += " ORDER BY s.Id"

    connection = Tortoise.get_connection('default')
    result = await connection.execute_query(sqlQuery, tuple(params))

    countQuery = """
        SELECT COUNT(*) from stockinputs WHERE branchItemId = %s
    """
    totalCountResult = await connection.execute_query(countQuery, (itemId,))
    totalCount = totalCountResult[1][0]['COUNT(*)']

    items = result[1]

    itemList = [
        {
            "id": item['id'],
            "qty": item['qty'],
            "moq": item['moq'],
            "deliveryDate": item['deliveryDate'],
            "deliveredBy": item['deliveredBy'],
            "expectedTotalQty": item['expectedQty'],
            "actualTotalQty": item['actualQty'],
            "branchItemId": item['branchItemId']
        }
        for item in items
    ]

    return create_response(True, 'Items Successfully Retrieved', itemList, None, totalCount), 200

async def getProductsHQ(categoryId, page=1, search=""):
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
            i.moq,
            c.name as categoryName,
            i.criticalValue,
            i.unitOfMeasure
        FROM items i
        INNER JOIN categories c on c.Id = i.categoryId
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
            "moq": item['moq'],
            "categoryName":item['categoryName'],
            "criticalValue":item['criticalValue'],
            "unitOfMeasure":item['unitOfMeasure']
        }
        for item in items
    ]

    return create_response(True, 'Items Successfully Retrieved', itemList, None, totalCount), 200

async def getProductHQ(itemId):
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
            i.moq,
            c.name as categoryName,
            i.criticalValue,
            i.unitOfMeasure
        FROM items i
        INNER JOIN categories c ON c.Id = i.categoryId
        WHERE i.id = %s
        LIMIT 1
    """

    params = (itemId,)

    connection = Tortoise.get_connection('default')
    result = await connection.execute_query(sqlQuery, params)

    items = result[1]

    if not items:
        return create_response(False, "Item not found", None), 404

    item = items[0]

    formatted_item = {
        "id": item['id'],
        "name": item['name'],
        "categoryId": item['categoryId'],
        "price": item['price'],
        "cost": item['cost'],
        "isManaged": item['isManaged'],
        "imagePath": item['imagePath'],
        "sellByUnit": bool(item['sellByUnit']),
        "moq": item['moq'],
        "categoryName": item['categoryName'],
        "criticalValue": item['criticalValue'],
        "unitOfMeasure": item['unitOfMeasure']
    }

    return create_response(True, "Item Successfully Retrieved", formatted_item), 200

async def createStockInput(stockInput):
    branchItem = await BranchItem.get_or_none(id=stockInput['branchItemId'])
    whItem = await WareHouseItem.get_or_none(itemId = branchItem.itemId)

    if not branchItem:
        return create_response(False, 'Item not found', None, None), 200

    await StockInput.create(
        qty=stockInput['qty'],
        deliveryDate=stockInput['deliveryDate'],
        deliveredBy=stockInput['deliveredBy'],
        expectedQty=stockInput['expectedTotalQty'],
        actualQty=stockInput['actualTotalQty'],
        branchItemId=branchItem.id
    )
    branchItem.quantity += Decimal(str(stockInput['qty']))
    whItem.quantity -= Decimal(str(stockInput['qty']))
    await branchItem.save()
    await whItem.save()
    
    return create_response(True, "Success", None, None), 200

async def saveItem(data, file):
    itemId = int(data.get('id'))
    name = data.get('name')
    price = Decimal(data.get('price'))
    cost = Decimal(data.get('cost'))
    categoryId = data.get('categoryId')
    moq = data.get('moq')
    sellByUnit = data.get('sellByUnit')
    if sellByUnit == 'true':
        sellByUnit = True
    else:
        sellByUnit = False

    criticalValue = data.get('criticalValue')
    unitOfMeasure = data.get('unitOfMeasure')

    if itemId == 0:
        item = await Item.create(
            categoryId=categoryId,
            price=price,
            cost=cost,
            moq= moq,
            name = name,
            sellByUnit = sellByUnit,
            unitOfMeasure = unitOfMeasure,
            isManaged = True,
            criticalValue = criticalValue
        )
        itemId = item.id

        branchItems = await Branch.all()

        for branch in branchItems:
            await BranchItem.create(
                itemId = itemId,
                branchId = branch.id,
                quantity = 0.00
            )
        
        await WareHouseItem.create(
            itemId = itemId,
            quantity = 0.00
        )

        message = "Item added successfully."

    else: 
        existing_item = await Item.get_or_none(id=itemId)
        if not existing_item:
            return create_response(False, "Customer not found.", None, None), 404

        existing_item.price = price
        existing_item.cost = cost
        existing_item.name = name
        existing_item.categoryId = categoryId
        existing_item.moq = moq
        existing_item.sellByUnit = sellByUnit
        existing_item.unitOfMeasure = unitOfMeasure
        existing_item.criticalValue = criticalValue

        cartItems = await CartItems.all()

        for i in cartItems:
            if(i.itemId == existing_item.id):
                await i.delete()
                
        await existing_item.save()

    if(file != None):
            result = upload_media(file)
            existing_item = await Item.get_or_none(id=itemId)
            existing_item.imagePath = result["secure_url"]
            existing_item.imageId = result["public_id"]
            await existing_item.save()

    return create_response(True, "Success", itemId, None), 200

async def deleteItem(id):
    item = await Item.get_or_none(id=id)
    
    if not item:
        return create_response(False, "Item not found.", None, None), 200

    item.isManaged = False
    if item.imagePath:
        result = delete_media(item.imageId)
        
    await item.save()
    
    return create_response(True, "Item deleted successfully.", None, None), 200

async def getStocksMonitor(categoryId, page=1, search=""):
    pageSize = 30
    offset = (page - 1) * pageSize

    sqlQuery = """
            SELECT i.id, i.name, b1.quantity as ppQty, "Branch: PuP" as ppName, "Branch: BSN" as snName, "Branch: Lab" as lName, 
                b2.quantity as snQty, b3.quantity as lQty, wh.quantity as whQty, "Warehouse" as whName,
                i.sellByUnit, i.criticalValue, i.imagePath, i.moq, b1.Id as ppId, b2.Id as snId, b3.Id as lId, wh.Id as whId
                FROM items i 
                LEFT JOIN branchitem b1 on b1.itemId = i.id and b1.branchId = 1
                LEFT JOIN branchitem b2 on b2.itemId = i.id and b2.branchId = 2
                LEFT JOIN branchitem b3 on b3.itemId = i.id and b3.branchId = 3
                LEFT JOIN warehouseitems wh on wh.itemId = i.id
                WHERE i.isManaged = 1
    """
    params = []

    if int(categoryId) == 1:
        sqlQuery += " AND (b1.quantity < i.criticalValue OR b2.quantity < i.criticalValue OR b3.quantity < i.criticalValue OR wh.quantity < i.criticalValue)"

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
                LEFT JOIN branchitem b1 on b1.itemId = i.id and b1.branchId = 1
                LEFT JOIN branchitem b2 on b2.itemId = i.id and b2.branchId = 2
                LEFT JOIN branchitem b3 on b3.itemId = i.id and b3.branchId = 3
                LEFT JOIN warehouseitems wh on wh.itemId = i.id
                WHERE i.isManaged = 1
    """
    totalCountResult = await connection.execute_query(countQuery)
    totalCount = totalCountResult[1][0]['COUNT(*)']

    items = result[1]

    itemList = [
        {
            "id": item['id'],
            "name": item['name'],
            "ppQty": Decimal(item['ppQty']),
            "ppName": item['ppName'],
            "snName": item['snName'],
            "lName": item['lName'],
            "snQty": Decimal(item['snQty']),
            "lQty": Decimal(item['lQty']),
            "whQty": Decimal(item['whQty']),
            "whName": item['whName'],
            "criticalValue": item['criticalValue'],
            "sellByUnit": bool(item['sellByUnit']),
            "imagePath" : item['imagePath'],
            "moq": item['moq'],
            "ppId": item['ppId'],
            "snId": item['snId'],
            "lId": item['lId'],
            "whId": item['whId']
        }
        for item in items
    ]

    return create_response(True, 'Items Successfully Retrieved', itemList, None, totalCount), 200
