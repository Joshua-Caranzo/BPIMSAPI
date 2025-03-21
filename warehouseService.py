from utils import create_response
from tortoise import Tortoise
from models import WHStockInput, WareHouseItem, Item, Supplier
from decimal import Decimal
from tortoise.queryset import Q 

async def getWHStocks(categoryId, page=1, search=""):
    pageSize = 30
    offset = (page - 1) * pageSize

    sqlQuery = """
       SELECT wh.id, i.name, wh.quantity, i.unitOfMeasure, i.criticalValue, i.sellByUnit, i.moq, i.imagePath
       FROM items i
        INNER JOIN warehouseitems wh ON wh.itemId = i.id
        WHERE i.isManaged = 1
    """
    params = []

    if int(categoryId) == 1:
        sqlQuery += " AND wh.quantity < i.criticalValue"

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
        INNER JOIN warehouseitems wh ON wh.itemId = i.id
        WHERE i.isManaged = 1
    """
    totalCountResult = await connection.execute_query(countQuery)
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
            "imagePath": item['imagePath']
        }
        for item in items
    ]

    return create_response(True, 'Items Successfully Retrieved', itemList, None, totalCount), 200

async def getStockHistory(itemId):
    sqlQuery = """
        SELECT s.*, i.moq, su.name as deliveredByName, i.name, i.sellByUnit from whstockinputs s
        INNER JOIN items i on i.id = s.itemId 
        inner join warehouseitems wh on wh.itemId = i.id
        LEFT JOIN suppliers su ON su.Id = s.deliveredBy
        WHERE wh.Id = %s
    """
    params = [itemId]

    sqlQuery += " ORDER BY s.Id"

    connection = Tortoise.get_connection('default')
    result = await connection.execute_query(sqlQuery, tuple(params))
    countQuery = """
        SELECT COUNT(*) from whstockinputs WHERE itemId = %s
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
            "deliveredByName": item['deliveredByName'],
            "expectedTotalQty": item['expectedQty'],
            "actualTotalQty": item['actualQty'],
            "name": item['name'],
            "sellByUnit": bool(item['sellByUnit'])
        }
        for item in items
    ]
    return create_response(True, 'Items Successfully Retrieved', itemList, None, totalCount), 200

async def createStockInput(stockInput):
    whItem = await WareHouseItem.get_or_none(id=stockInput['id'])
    item = await Item.get_or_none(id = whItem.itemId)

    if not whItem:
        return create_response(False, 'Item not found', None, None), 400

    await WHStockInput.create(
        qty=stockInput['qty'],
        moq=item.moq,
        deliveryDate=stockInput['deliveryDate'],
        deliveredBy=stockInput['deliveredBy'],
        expectedQty=stockInput['expectedTotalQty'],
        actualQty=stockInput['actualTotalQty'],
        itemId=whItem.itemId
    )
    whItem.quantity += Decimal(str(stockInput['qty']))

    await whItem.save()

    return create_response(True, "Success", None, None), 200

async def getSupplierList(search = ""):

    supplierQuery = Supplier.all().order_by('name')

    if search:
        supplierQuery = supplierQuery.filter(Q(name__icontains=search))

    supliers = await supplierQuery.values("id", "name")

    return create_response(True, "Customer list retrieved successfully.", supliers, None), 200

async def getSupplier(id):
    if id:
        supplier = await Supplier.get_or_none(id=id)
        
        if supplier:            
            supplierData = {
                'id': supplier.id,
                'name': supplier.name,
                'contactNumber1': supplier.contactNumber1,
                'contactNumber2': supplier.contactNumber2,
                'address': supplier.address
            }

            message = "Supplier successfully retrieved"
            return create_response(True, message, supplierData, None), 200 
        else:
            message = "Supplier not found"
    else:
        message = "No Supplier Retrieved"

    return create_response(False, message, None, None), 200

async def saveSupplier(supplier):
    if(supplier['id'] == 0):
        await Supplier.create(
            name = supplier['name'],
            address = supplier['address'],
            contactNumber1 = supplier['contactNumber1'],
            contactNumber2 = supplier['contactNumber2'],
        )
    else:
        existingSupplier = await Supplier.get_or_none(id = supplier['id'])
        existingSupplier.name = supplier['name']
        existingSupplier.address = supplier['address']
        existingSupplier.contactNumber1 = supplier['contactNumber1']
        existingSupplier.contactNumber2 = supplier['contactNumber2']
        await existingSupplier.save()

    return create_response(True, "Success", None, None), 200

async def removeSupplier(id):
    existingSupplier = await Supplier.get_or_none(id=id)
    
    if not existingSupplier:
        return create_response(False, "Supplier not found", None, None), 404 

    whStockHistory = await WHStockInput.filter(deliveredBy=existingSupplier.id).all() 

    for stock in whStockHistory:
        stock.deliveredBy = None  
        await stock.save()

    await existingSupplier.delete() 

    return create_response(True, "Success", None, None), 200

async def getSupplierStockHistory(supplierId):
    sqlQuery = """
        SELECT s.*, i.moq, su.name as deliveredByName, i.name, i.sellByUnit from whstockinputs s
        INNER JOIN items i on i.id = s.itemId 
        inner join warehouseitems wh on wh.itemId = i.id
        INNER JOIN suppliers su ON su.Id = s.deliveredBy
        WHERE su.Id = %s
    """
    params = [supplierId]

    sqlQuery += " ORDER BY s.Id"

    connection = Tortoise.get_connection('default')
    result = await connection.execute_query(sqlQuery, tuple(params))
    countQuery = """
        SELECT COUNT(*) from whstockinputs s
        INNER JOIN suppliers su ON su.Id = s.deliveredBy
        WHERE su.id = %s
    """
    totalCountResult = await connection.execute_query(countQuery, (supplierId,))
    totalCount = totalCountResult[1][0]['COUNT(*)']

    items = result[1]

    itemList = [
        {
            "id": item['id'],
            "qty": item['qty'],
            "moq": item['moq'],
            "deliveryDate": item['deliveryDate'],
            "deliveredBy": item['deliveredBy'],
            "deliveredByName": item['deliveredByName'],
            "expectedTotalQty": item['expectedQty'],
            "actualTotalQty": item['actualQty'],
            "name": item['name'],
            "sellByUnit": bool(item['sellByUnit'])
        }
        for item in items
    ]
    return create_response(True, 'Items Successfully Retrieved', itemList, None, totalCount), 200
