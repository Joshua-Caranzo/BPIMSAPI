from models import BranchTransferHistory, BranchItem, BranchReturn, WareHouseItem
from utils import create_response
from tortoise import Tortoise
from decimal import Decimal
from datetime import datetime

async def saveBranchTransfer(branchTransfer):
    branchItemFrom = await BranchItem.get_or_none(id=branchTransfer['branchFromId'])
    branchItemTo = await BranchItem.get_or_none(branchId=branchTransfer['branchToId'], itemId = branchItemFrom.itemId)

    if not branchItemTo or not branchItemFrom:
        return create_response(False, "Invalid branch ID", None, None), 400

    await BranchTransferHistory.create(
        branchFromId=branchItemFrom.id,
        branchToId=branchItemTo.id,
        quantity=branchTransfer['quantity'],
        date=datetime.now() 
    )

    branchItemTo.quantity += Decimal(branchTransfer['quantity'])
    branchItemFrom.quantity -= Decimal(branchTransfer['quantity'])

    await branchItemTo.save()
    await branchItemFrom.save()

    return create_response(True, "Success", None, None), 200

async def getBranchTransferHistory(branchItemId):

    sqlQuery = """
           SELECT bh.id, bh.quantity, bh.date, bh.branchFromId, bh.branchToId, br1.Name as branchFrom, br2.Name as branchTo
           FROM branchtransferhistory bh
           INNER JOIN branchItem b1 on b1.Id = bh.branchFromId
           INNER JOIN branchItem b2 on b2.Id = bh.branchToId
           INNER JOIN branches br1 on br1.Id = b1.branchId
           INNER JOIN branches br2 on br2.Id = b2.branchId
           WHERE bh.branchFromId = %s OR bh.branchToId = %s
        """
    params = [branchItemId, branchItemId]

    connection = Tortoise.get_connection('default')
    result = await connection.execute_query(sqlQuery, tuple(params))

    history = result[1]

    historyList = [
        {
            "id": h['id'],
            "date": h['date'],
            "quantity": h['quantity'],
            "branchFrom": h['branchFrom'],
            "branchTo": h['branchTo'],
            "branchFromId": h['branchFromId'],
            "branchToId": h['branchToId']
        }
        for h in history
    ]

    return create_response(True, "Success", historyList, None), 200

async def returnToWH(returnStock):
    branchItemId = await BranchItem.get_or_none(id=returnStock['branchItemId'])
    whItem = await WareHouseItem.get_or_none(itemId = branchItemId.itemId)

    if not branchItemId:
        return create_response(False, 'Item not found', None, None), 200

    if not whItem:
        return create_response(False, 'Item not found', None, None), 200

    await BranchReturn.create(
        branchItemId=returnStock['branchItemId'],
        reason=returnStock['reason'],
        quantity=Decimal(str(returnStock['quantity'])),
        date=datetime.now()
    )

    branchItemId.quantity -= Decimal(str(returnStock['quantity']))
    whItem.quantity += Decimal(str(returnStock['quantity']))
    await branchItemId.save()
    await whItem.save()

    return create_response(True, "Success", None, None), 200

async def getBranchReturnHistory(branchItemId):
    sqlQuery = """
        SELECT br.id, br.branchItemId, br.reason, br.quantity, br.date
        FROM branchreturn br
        WHERE br.branchItemId = %s
        ORDER BY br.id
    """
    params = [branchItemId]

    connection = Tortoise.get_connection('default')
    result = await connection.execute_query(sqlQuery, tuple(params))

    countQuery = "SELECT COUNT(*) FROM branchreturn WHERE branchItemId = %s"
    totalCountResult = await connection.execute_query(countQuery, (branchItemId,))
    totalCount = totalCountResult[1][0]['COUNT(*)']

    items = result[1]

    itemList = [
        {
            "id": item['id'],
            "branchItemId": item['branchItemId'],
            "reason": item['reason'],
            "quantity": item['quantity'],
            "date": item['date']
        }
        for item in items
    ]

    return create_response(True, 'Return to Warehouse History Retrieved Successfully', itemList, None, totalCount), 200
