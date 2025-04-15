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
                    COALESCE(i.categoryId, 0) AS categoryId, 
                    i.price, 
                    i.cost, 
                    i.isManaged, 
                    i.imagePath, 
                    bi.quantity,
                    i.sellByUnit,
                    COUNT(ti.itemId) AS total_sales,
                    bi.id as branchItemId
                FROM transactionitems ti
                JOIN items i ON ti.itemId = i.id
                JOIN transactions tr ON ti.transactionId = tr.id AND tr.isVoided = 0
                JOIN branches b ON tr.branchId = b.id
                JOIN branchitem bi ON bi.itemId = i.id AND bi.branchId = b.id
                WHERE b.id = %s AND i.isManaged = 1
                GROUP BY i.id, i.name, i.categoryId, i.price, i.cost, i.isManaged, i.imagePath, bi.quantity, i.sellByUnit, bi.id
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
                COALESCE(i.categoryId, 0) AS categoryId, 
                i.price, 
                i.cost, 
                i.isManaged, 
                i.imagePath, 
                bi.quantity,
                i.sellByUnit,
                bi.id as branchItemId
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
            "sellByUnit": bool(item['sellByUnit']),
            "branchItemId": item['branchItemId']
        }
        for item in items
    ]

    return create_response(True, 'Items Successfully Retrieved', itemList, None, totalCount), 200


async def getBranchStocks(categoryId, branchId, page=1, search=""):
    pageSize = 30
    offset = (page - 1) * pageSize

    sqlQuery = """
        SELECT bi.id, i.name, bi.quantity, i.unitOfMeasure, i.storeCriticalValue, i.sellByUnit, i.whCriticalValue, wi.quantity as whQuantity, i.imagePath FROM items i 
        INNER JOIN branchitem bi ON bi.itemId = i.id
        INNER JOIN warehouseitems wi ON wi.itemId = i.id
        WHERE bi.branchId = %s AND i.isManaged = 1
    """
    params = [branchId]

    if int(categoryId) == 1:
        sqlQuery += " AND bi.quantity < i.storeCriticalValue"

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
            "whCriticalValue": item['whCriticalValue'],
            "sellByUnit": bool(item['sellByUnit']),
            "storeCriticalValue": item['storeCriticalValue'],
            "imagePath": item['imagePath'],
            "whQty": item['whQuantity']
        }
        for item in items
    ]
    return create_response(True, 'Items Successfully Retrieved', itemList, None, totalCount), 200

async def getStockHistory(itemId):
    sqlQuery = """
        SELECT s.*, i.storeCriticalValue from stockinputs s inner join branchitem bi on s.branchItemId= bi.id
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
            "storeCriticalValue": item['storeCriticalValue'],
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
            COALESCE(i.categoryId, 0) AS categoryId, 
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
        LEFT JOIN categories c ON c.Id = i.categoryId
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
        "storeCriticalValue": item['storeCriticalValue'],
        "categoryName": item['categoryName'],
        "whCriticalValue": item['whCriticalValue'],
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
    categoryId = None if data.get('categoryId') == '0' else data.get('categoryId')
    storeCriticalValue = data.get('storeCriticalValue')
    sellByUnit = data.get('sellByUnit')
    if sellByUnit == 'true':
        sellByUnit = True
    else:
        sellByUnit = False

    whCriticalValue = data.get('whCriticalValue')
    unitOfMeasure = data.get('unitOfMeasure')

    if itemId == 0:
        item = await Item.create(
            categoryId=categoryId,
            price=price,
            cost=cost,
            storeCriticalValue= storeCriticalValue,
            name = name,
            sellByUnit = sellByUnit,
            unitOfMeasure = unitOfMeasure,
            isManaged = True,
            whCriticalValue = whCriticalValue
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
        existing_item.storeCriticalValue = storeCriticalValue
        existing_item.sellByUnit = sellByUnit
        existing_item.unitOfMeasure = unitOfMeasure
        existing_item.whCriticalValue = whCriticalValue

        cartItems = await CartItems.all()

        for i in cartItems:
            branchItem = await BranchItem.get_or_none(id = i.branchItemId)
            if(branchItem.itemId == existing_item.id):
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

    connection = Tortoise.get_connection('default')
    branches = await connection.execute_query("SELECT id, name FROM branches WHERE isActive = 1")
    branch_list = branches[1]
    
    branch_joins = []
    branch_selects = []
    branch_names = []
    branch_ids = []
    critical_conditions = []
    
    for branch in branch_list:
        alias = f"b{branch['id']}"
        branch_joins.append(f"LEFT JOIN branchitem {alias} on {alias}.itemId = i.id and {alias}.branchId = {branch['id']}")
        branch_selects.append(f"{alias}.quantity as branch_{branch['id']}_qty")
        branch_names.append(f"'Branch: {branch['name']}' as branch_{branch['id']}_name")
        branch_ids.append(f"{alias}.Id as branch_{branch['id']}_id")
        critical_conditions.append(f"{alias}.quantity < i.storeCriticalValue")

    sqlQuery = f"""
        SELECT 
            i.id, 
            i.name, 
            {', '.join(branch_selects)},
            {', '.join(branch_names)},
            wh.quantity as whQty, 
            "Warehouse" as whName,
            i.sellByUnit, 
            i.whCriticalValue, 
            i.imagePath, 
            i.storeCriticalValue, 
            {', '.join(branch_ids)},
            wh.Id as whId,
            i.unitOfMeasure
        FROM items i 
        {' '.join(branch_joins)}
        LEFT JOIN warehouseitems wh on wh.itemId = i.id
        WHERE i.isManaged = 1
    """
    
    params = []

    if int(categoryId) == 1:
        all_critical_conditions = " OR ".join(critical_conditions + ["wh.quantity < i.whCriticalValue"])
        sqlQuery += f" AND ({all_critical_conditions})"

    if search:
        sqlQuery += " AND i.name LIKE %s"
        params.append(f'%{search}%')

    sqlQuery += " ORDER BY i.name"
    sqlQuery += " LIMIT %s OFFSET %s"
    params.extend([pageSize, offset])

    result = await connection.execute_query(sqlQuery, tuple(params))

    countQuery = f"""
        SELECT COUNT(*) 
        FROM items i 
        {' '.join(branch_joins)}
        LEFT JOIN warehouseitems wh on wh.itemId = i.id
        WHERE i.isManaged = 1
    """
    
    if int(categoryId) == 1:
        countQuery += f" AND ({all_critical_conditions})"
    
    if search:
        countQuery += " AND i.name LIKE %s"
    
    totalCountResult = await connection.execute_query(countQuery, tuple(params[:-2]))
    totalCount = totalCountResult[1][0]['COUNT(*)']

    items = result[1]
    itemList = []
    
    for item in items:
        item_data = {
            "id": item['id'],
            "name": item['name'],
            "whQty": Decimal(item['whQty']),
            "whName": item['whName'],
            "whCriticalValue": item['whCriticalValue'],
            "sellByUnit": bool(item['sellByUnit']),
            "imagePath": item['imagePath'],
            "storeCriticalValue": item['storeCriticalValue'],
            "whId": item['whId'],
            "unitOfMeasure": item['unitOfMeasure'],
            "branches": []
        }
        
        for branch in branch_list:
            branch_id = branch['id']
            item_data["branches"].append({
                "id": item[f'branch_{branch_id}_id'],
                "name": item[f'branch_{branch_id}_name'],
                "quantity": Decimal(item[f'branch_{branch_id}_qty']),
                "branchId": branch_id
            })
        
        itemList.append(item_data)

    return create_response(True, 'Items Successfully Retrieved', itemList, None, totalCount), 200

async def getWHStocksMonitor(categoryId, page=1, search=""):
    pageSize = 30
    offset = (page - 1) * pageSize

    connection = Tortoise.get_connection('default')
    branches = await connection.execute_query("SELECT id, name FROM branches WHERE isActive = 1")
    branch_list = branches[1]
    
    branch_joins = []
    branch_selects = []
    branch_ids = []
    critical_conditions = []
    
    for branch in branch_list:
        alias = f"b{branch['id']}"
        branch_joins.append(f"LEFT JOIN branchitem {alias} on {alias}.itemId = i.id and {alias}.branchId = {branch['id']}")
        branch_selects.append(f"{alias}.quantity as branch_{branch['id']}_qty")
        branch_selects.append(f"b{branch['id']}.branchId as branch_{branch['id']}_id")
        branch_ids.append(f"{alias}.Id as branch_{branch['id']}_item_id")
        critical_conditions.append(f"{alias}.quantity < i.storeCriticalValue")

    sqlQuery = f"""
        SELECT 
            i.id, 
            i.name, 
            {', '.join(branch_selects)},
            {', '.join(branch_ids)},
            i.sellByUnit, 
            i.imagePath, 
            i.storeCriticalValue,
            i.unitOfMeasure
        FROM items i 
        {' '.join(branch_joins)}
        WHERE i.isManaged = 1
    """
    
    params = []

    if int(categoryId) == 1:
        all_critical_conditions = " OR ".join(critical_conditions)
        sqlQuery += f" AND ({all_critical_conditions})"

    if search:
        sqlQuery += " AND i.name LIKE %s"
        params.append(f'%{search}%')

    sqlQuery += " ORDER BY i.name"
    sqlQuery += " LIMIT %s OFFSET %s"
    params.extend([pageSize, offset])

    result = await connection.execute_query(sqlQuery, tuple(params))

    countQuery = f"""
        SELECT COUNT(*) 
        FROM items i 
        {' '.join(branch_joins)}
        WHERE i.isManaged = 1
    """
    
    if int(categoryId) == 1:
        countQuery += f" AND ({all_critical_conditions})"
    
    if search:
        countQuery += " AND i.name LIKE %s"
    
    totalCountResult = await connection.execute_query(countQuery, tuple(params[:-2]))
    totalCount = totalCountResult[1][0]['COUNT(*)']

    items = result[1]
    itemList = []
    
    branch_name_map = {branch['id']: branch['name'] for branch in branch_list}
    
    for item in items:
        item_data = {
            "id": item['id'],
            "name": item['name'],
            "sellByUnit": bool(item['sellByUnit']),
            "imagePath": item['imagePath'],
            "storeCriticalValue": item['storeCriticalValue'],
            "unitOfMeasure": item['unitOfMeasure'],
            "branches": []
        }
        
        for branch in branch_list:
            branch_id = branch['id']
            item_data["branches"].append({
                "id": item[f'branch_{branch_id}_item_id'],
                "branchId": branch_id,
                "name": branch_name_map[branch_id],
                "quantity": Decimal(item[f'branch_{branch_id}_qty']) if item[f'branch_{branch_id}_qty'] is not None else Decimal(0)
            })
        
        itemList.append(item_data)

    return create_response(True, 'Items Successfully Retrieved', itemList, None, totalCount), 200

async def editStock(id, qty):
    branchItem = await BranchItem.get_or_none(id=id)
    if not branchItem:
        return create_response(False, 'Item not found', None, None), 200

    branchItem.quantity = Decimal(str(qty))
    await branchItem.save()
    
    return create_response(True, "Success", None, None), 200