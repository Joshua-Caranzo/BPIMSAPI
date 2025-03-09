
from tortoise import Tortoise
import asyncio
import datetime

async def criticalItems(websocket, branchId):
    while True:
        count_query = f"""
            SELECT COUNT(*) as critical_count
            FROM branchitem bi
            INNER JOIN items i ON i.id = bi.itemid
            WHERE i.criticalValue > bi.quantity
            AND bi.branchId = {branchId} AND i.isManaged = 1
        """
        connection = Tortoise.get_connection('default')
        result = await connection.execute_query_dict(count_query)

        critical_count = result[0]['critical_count']
        await websocket.send(str(critical_count)) 

        await asyncio.sleep(5)

def get_time_periods():
    current_time = datetime.datetime.now().time()

    periods = [
        {"id": 1, "start": datetime.time(7, 0), "end": datetime.time(9, 30), "label": "7-9:30 AM"},
        {"id": 2, "start": datetime.time(9, 31), "end": datetime.time(12, 0), "label": "9:30-12:00 PM"},
        {"id": 3, "start": datetime.time(12, 1), "end": datetime.time(14, 30), "label": "12:00-2:30 PM"},
        {"id": 4, "start": datetime.time(14, 31), "end": datetime.time(17, 0), "label": "2:30-5:00 PM"},
    ]

    periods_to_include = []
    
    for period in periods:
        if period["start"] <= current_time <= period["end"]:
            periods_to_include.append(period)

        if period["end"] < current_time:
            periods_to_include.append(period)

    return periods_to_include

async def dailyTransaction(websocket, branchId):
    while True:
        periods_to_include = get_time_periods()
        totalAmountPerPeriod = {}

        connection = Tortoise.get_connection('default')

        for period in periods_to_include:
            transactionQuery = f"""
                SELECT tr.totalAmount
                FROM transactions tr
                INNER JOIN users u ON u.id = tr.cashierId
                WHERE DATE(tr.transactionDate) = CURDATE()
                AND TIME(tr.transactionDate) BETWEEN '{period["start"]}' AND '{period["end"]}'
                AND tr.branchId = {branchId}
                ORDER BY tr.transactionDate;
            """
            
            transactions = await connection.execute_query_dict(transactionQuery)

            total_amount = sum(float(tr["totalAmount"]) for tr in transactions)
            totalAmountPerPeriod[period["id"]] = total_amount

        graphDataDto = [
            {"periodId": period["id"], "totalAmount": totalAmountPerPeriod.get(period["id"], 0.0)}
            for period in periods_to_include
        ]

        dailyTransactsDto = f"""
            SELECT tr.id, tr.totalAmount, tr.slipNo, tr.transactionDate, u.name as cashierName
            FROM transactions tr
            INNER JOIN users u ON u.id = tr.cashierId
            WHERE DATE(tr.transactionDate) = CURDATE()
            AND tr.branchId = {branchId}
            ORDER BY tr.transactionDate;
        """
        
        dailyTransactions = await connection.execute_query_dict(dailyTransactsDto)

        transactionsDto = []

        for tr in dailyTransactions:
            itemsQuery = """
                SELECT ti.id, i.name as itemName, i.id as itemId, ti.quantity 
                FROM transactionitems ti
                INNER JOIN items i ON i.id = ti.itemId
                WHERE ti.transactionId = %s
            """
            items = await connection.execute_query_dict(itemsQuery, (tr['id'],))

            transactionsDto.append({
                "id": tr["id"],
                "totalAmount": float(tr["totalAmount"]),
                "slipNo": tr["slipNo"],
                "transactionDate":  tr["transactionDate"],
                "cashierName": tr["cashierName"],
                "items": items 
            })

        response = {
            "graphData": graphDataDto,
            "transactions": transactionsDto
        }

        await websocket.send_json(response)

        await asyncio.sleep(1)

async def totalSales(websocket, branchId):
    while True:
        connection = Tortoise.get_connection('default')

        totalSalesYearQuery = f"""
            SELECT SUM(totalAmount) AS totalSales
            FROM transactions
            WHERE YEAR(transactionDate) = YEAR(CURDATE())
            AND branchId = {branchId}
        """
        totalSalesPerYear = await connection.execute_query_dict(totalSalesYearQuery)

        totalSalesMonthQuery = f"""
            SELECT SUM(totalAmount) AS totalSales
            FROM transactions
            WHERE YEAR(transactionDate) = YEAR(CURDATE()) AND MONTH(transactionDate) = MONTH(CURDATE())
            AND branchId = {branchId}
        """
        totalSalesPerMonth = await connection.execute_query_dict(totalSalesMonthQuery)

        totalSalesYear = totalSalesPerYear[0]["totalSales"] if totalSalesPerYear and totalSalesPerYear[0]["totalSales"] else 0.0
        totalSalesMonth = totalSalesPerMonth[0]["totalSales"] if totalSalesPerMonth and totalSalesPerMonth[0]["totalSales"] else 0.0

        response = {
            "totalSalesPerYear": float(totalSalesYear),
            "totalSalesPerMonth": float(totalSalesMonth)
        }

        await websocket.send_json(response)

        await asyncio.sleep(1)

async def dailyTransactionHQ(websocket):
    while True:
        connection = Tortoise.get_connection('default')

        branchTransactionQuery = """
            SELECT 
                b.name AS branchName, 
                COALESCE(SUM(tr.totalAmount), 0) AS dailyTotal,
                COALESCE(SUM(tr.profit), 0) AS totalProfit
            FROM branches b
            LEFT JOIN transactions tr 
                ON tr.branchId = b.Id 
                AND DATE(tr.transactionDate) = CURDATE()
            GROUP BY b.id;
        """

        branchTransactions = await connection.execute_query_dict(branchTransactionQuery)

        topItemsQuery = """
            WITH RankedItems AS (
            SELECT 
                b.name AS branchName, 
                i.name AS itemName, 
                SUM(ti.Amount) AS totalSales,
                ROW_NUMBER() OVER (PARTITION BY b.id ORDER BY SUM(ti.Amount) DESC) AS `rank`
            FROM transactionitems ti
            JOIN items i ON ti.itemId = i.id
            JOIN transactions tr ON ti.transactionId = tr.id
            JOIN branches b ON tr.branchId = b.id
            WHERE DATE(tr.transactionDate) = CURDATE()
            GROUP BY b.id, i.id
        )
        SELECT branchName, itemName, totalSales
        FROM RankedItems
        WHERE `rank` <= 5;
        """

        topItems = await connection.execute_query_dict(topItemsQuery)

        total_amount = sum(tr["dailyTotal"] for tr in branchTransactions)
        total_profit = sum(tr["totalProfit"] for tr in branchTransactions)

        branch_items_map = {}
        for item in topItems:
            branch_name = item["branchName"]
            if branch_name not in branch_items_map:
                branch_items_map[branch_name] = []
            branch_items_map[branch_name].append({
                "itemName": item["itemName"],
                "totalSales": float(item["totalSales"])
            })

        response = {
            "branches": [
                {
                    "name": tr["branchName"],
                    "dailyTotal": float(tr["dailyTotal"]),
                    "totalProfit": float(tr["totalProfit"]),
                    "topItems": branch_items_map.get(tr["branchName"], [])  
                }
                for tr in branchTransactions
            ],
            "totalAmount": float(total_amount),
            "totalProfit": float(total_profit)
        }

        await websocket.send_json(response)

        await asyncio.sleep(1)

async def totalSalesHQ(websocket):
    while True:
        connection = Tortoise.get_connection('default')

        totalSalesYearQuery = f"""
            SELECT SUM(totalAmount) AS totalSales
            FROM transactions
            WHERE YEAR(transactionDate) = YEAR(CURDATE())
        """
        totalSalesPerYear = await connection.execute_query_dict(totalSalesYearQuery)

        totalSalesMonthQuery = f"""
            SELECT SUM(totalAmount) AS totalSales
            FROM transactions
            WHERE YEAR(transactionDate) = YEAR(CURDATE()) AND MONTH(transactionDate) = MONTH(CURDATE())
        """
        totalSalesPerMonth = await connection.execute_query_dict(totalSalesMonthQuery)

        totalSalesYear = totalSalesPerYear[0]["totalSales"] if totalSalesPerYear and totalSalesPerYear[0]["totalSales"] else 0.0
        totalSalesMonth = totalSalesPerMonth[0]["totalSales"] if totalSalesPerMonth and totalSalesPerMonth[0]["totalSales"] else 0.0

        response = {
            "totalSalesPerYear": float(totalSalesYear),
            "totalSalesPerMonth": float(totalSalesMonth)
        }

        await websocket.send_json(response)

        await asyncio.sleep(1)

async def criticalItemsHQ(websocket):
    while True:
        count_query = f"""
            SELECT COUNT(*) as critical_count
            FROM branchitem bi
            INNER JOIN items i ON i.id = bi.itemid
            WHERE i.criticalValue > bi.quantity
            AND i.isManaged = 1
        """
        connection = Tortoise.get_connection('default')
        result = await connection.execute_query_dict(count_query)

        bi_critical_count = result[0]['critical_count']

        wi_count_query = f"""
            SELECT COUNT(*) as critical_count
            FROM warehouseitems bi
            INNER JOIN items i ON i.id = bi.itemid
            WHERE i.criticalValue > bi.quantity
            AND i.isManaged = 1
        """
        connection = Tortoise.get_connection('default')
        result = await connection.execute_query_dict(wi_count_query)

        wi_critical_count = result[0]['critical_count']
        critical_count = bi_critical_count + wi_critical_count
        await websocket.send(str(critical_count)) 

        await asyncio.sleep(5)

async def criticalItemsWH(websocket):
    while True:
        wi_count_query = f"""
            SELECT COUNT(*) as critical_count
            FROM warehouseitems bi
            INNER JOIN items i ON i.id = bi.itemid
            WHERE i.criticalValue > bi.quantity
            AND i.isManaged = 1
        """
        connection = Tortoise.get_connection('default')
        result = await connection.execute_query_dict(wi_count_query)

        critical_count = result[0]['critical_count']
        await websocket.send(str(critical_count)) 

        await asyncio.sleep(5)
