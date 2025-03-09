from utils import create_response
from tortoise import Tortoise
from models import WHStockInput, WareHouseItem, Item
from decimal import Decimal

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
        SELECT s.*, i.moq from whstockinputs s
        INNER JOIN items i on i.id = s.itemId 
        inner join warehouseitems wh on wh.itemId = i.id 
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
            "expectedTotalQty": item['expectedQty'],
            "actualTotalQty": item['actualQty']
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