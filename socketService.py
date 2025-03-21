
from tortoise import Tortoise
import asyncio
from datetime import datetime, time, timezone, timedelta

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
    # Get current Singapore time (UTC+8)
    now_sg = datetime.now(timezone.utc) + timedelta(hours=8)
    current_time = now_sg.time()

    periods = [
        {"id": 1, "start": time(7, 0), "end": time(9, 30), "label": "7-9:30 AM"},
        {"id": 2, "start": time(9, 31), "end": time(12, 0), "label": "9:30-12:00 PM"},
        {"id": 3, "start": time(12, 1), "end": time(14, 30), "label": "12:00-2:30 PM"},
        {"id": 4, "start": time(14, 31), "end": time(17, 0), "label": "2:30-5:00 PM"},
    ]

    periods_to_include = []

    for period in periods:
        if period["start"] <= current_time <= period["end"]:
            periods_to_include.append(period)
        elif period["end"] < current_time:
            periods_to_include.append(period)

    return periods_to_include

async def dailyTransaction(websocket, branchId):
    while True:
        now_sg = datetime.now(timezone.utc) + timedelta(hours=8)
        singapore_date = now_sg.date()

        periods_to_include = get_time_periods()
        totalAmountPerPeriod = {}

        connection = Tortoise.get_connection('default')

        for period in periods_to_include:
            transactionQuery = f"""
                SELECT tr.totalAmount
                FROM transactions tr
                INNER JOIN users u ON u.id = tr.cashierId
                WHERE DATE(tr.transactionDate) = '{singapore_date}'
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
            WHERE DATE(tr.transactionDate) = '{singapore_date}'
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
                "transactionDate": tr["transactionDate"],
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
        now_sg = datetime.now(timezone.utc) + timedelta(hours=8)
        singapore_year = now_sg.year
        singapore_month = now_sg.month

        connection = Tortoise.get_connection('default')

        totalSalesYearQuery = f"""
            SELECT SUM(totalAmount) AS totalSales
            FROM transactions
            WHERE YEAR(transactionDate) = {singapore_year}
            AND branchId = {branchId}
        """
        totalSalesPerYear = await connection.execute_query_dict(totalSalesYearQuery)

        totalSalesMonthQuery = f"""
            SELECT SUM(totalAmount) AS totalSales
            FROM transactions
            WHERE YEAR(transactionDate) = {singapore_year} AND MONTH(transactionDate) = {singapore_month}
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
        now_sg = datetime.now(timezone.utc) + timedelta(hours=8)
        singapore_date = now_sg.date()

        connection = Tortoise.get_connection('default')

        branchTransactionQuery = f"""
            SELECT 
                b.name AS branchName, 
                COALESCE(SUM(tr.totalAmount), 0) AS dailyTotal,
                COALESCE(SUM(tr.profit), 0) AS totalProfit
            FROM branches b
            LEFT JOIN transactions tr 
                ON tr.branchId = b.Id 
                AND DATE(tr.transactionDate) = '{singapore_date}'
            GROUP BY b.id;
        """

        branchTransactions = await connection.execute_query_dict(branchTransactionQuery)

        topItemsQuery = f"""
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
            WHERE DATE(tr.transactionDate) = '{singapore_date}'
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
        now_sg = datetime.now(timezone.utc) + timedelta(hours=8)
        singapore_year = now_sg.year
        singapore_month = now_sg.month

        connection = Tortoise.get_connection('default')

        totalSalesYearQuery = f"""
            SELECT SUM(totalAmount) AS totalSales
            FROM transactions
            WHERE YEAR(transactionDate) = {singapore_year}
        """
        totalSalesPerYear = await connection.execute_query_dict(totalSalesYearQuery)

        totalSalesMonthQuery = f"""
            SELECT SUM(totalAmount) AS totalSales
            FROM transactions
            WHERE YEAR(transactionDate) = {singapore_year} 
            AND MONTH(transactionDate) = {singapore_month}
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

async def analyticsData(websocket, branch_id=1):
    while True:
        now_sg = datetime.now(timezone.utc) + timedelta(hours=8)
        connection = Tortoise.get_connection('default')
        singapore_year = now_sg.year
        singapore_month = now_sg.month
        singapore_date = now_sg.date()

        queries = {
            "Week": f"""
                SELECT 
                    COALESCE(SUM(CASE WHEN WEEKDAY(tr.transactionDate) = 0 THEN tr.totalAmount END), 0) AS Monday,
                    COALESCE(SUM(CASE WHEN WEEKDAY(tr.transactionDate) = 1 THEN tr.totalAmount END), 0) AS Tuesday,
                    COALESCE(SUM(CASE WHEN WEEKDAY(tr.transactionDate) = 2 THEN tr.totalAmount END), 0) AS Wednesday,
                    COALESCE(SUM(CASE WHEN WEEKDAY(tr.transactionDate) = 3 THEN tr.totalAmount END), 0) AS Thursday,
                    COALESCE(SUM(CASE WHEN WEEKDAY(tr.transactionDate) = 4 THEN tr.totalAmount END), 0) AS Friday,
                    COALESCE(SUM(CASE WHEN WEEKDAY(tr.transactionDate) = 5 THEN tr.totalAmount END), 0) AS Saturday
                FROM transactions tr
                INNER JOIN users u ON u.id = tr.cashierId
                WHERE DATE(tr.transactionDate) BETWEEN 
                    DATE_SUB('{singapore_date}', INTERVAL WEEKDAY('{singapore_date}') DAY) 
                    AND 
                    DATE_SUB('{singapore_date}', INTERVAL WEEKDAY('{singapore_date}') - 5 DAY)
                AND tr.branchId = {branch_id};
            """,
            "Month": f"""
                SELECT 
                    COALESCE(SUM(CASE WHEN tr.transactionDate BETWEEN DATE_FORMAT('{singapore_date}', '%Y-%m-01') 
                                      AND DATE_ADD(DATE_FORMAT('{singapore_date}', '%Y-%m-01'), INTERVAL 6 DAY) THEN tr.totalAmount END), 0) AS Week_1,
                    COALESCE(SUM(CASE WHEN tr.transactionDate BETWEEN DATE_ADD(DATE_FORMAT('{singapore_date}', '%Y-%m-01'), INTERVAL 7 DAY) 
                                      AND DATE_ADD(DATE_FORMAT('{singapore_date}', '%Y-%m-01'), INTERVAL 13 DAY) THEN tr.totalAmount END), 0) AS Week_2,
                    COALESCE(SUM(CASE WHEN tr.transactionDate BETWEEN DATE_ADD(DATE_FORMAT('{singapore_date}', '%Y-%m-01'), INTERVAL 14 DAY) 
                                      AND DATE_ADD(DATE_FORMAT('{singapore_date}', '%Y-%m-01'), INTERVAL 20 DAY) THEN tr.totalAmount END), 0) AS Week_3,
                    COALESCE(SUM(CASE WHEN tr.transactionDate BETWEEN DATE_ADD(DATE_FORMAT('{singapore_date}', '%Y-%m-01'), INTERVAL 21 DAY) 
                                      AND LAST_DAY('{singapore_date}') THEN tr.totalAmount END), 0) AS Week_4
                FROM transactions tr
                WHERE MONTH(tr.transactionDate) = {singapore_month} AND YEAR(tr.transactionDate) = {singapore_year} AND tr.branchId = {branch_id};
            """,
            "Year": f"""
                SELECT 
                    COALESCE(SUM(CASE WHEN MONTH(tr.transactionDate) = 1 THEN tr.totalAmount END), 0) AS Jan,
                    COALESCE(SUM(CASE WHEN MONTH(tr.transactionDate) = 2 THEN tr.totalAmount END), 0) AS Feb,
                    COALESCE(SUM(CASE WHEN MONTH(tr.transactionDate) = 3 THEN tr.totalAmount END), 0) AS Mar,
                    COALESCE(SUM(CASE WHEN MONTH(tr.transactionDate) = 4 THEN tr.totalAmount END), 0) AS Apr,
                    COALESCE(SUM(CASE WHEN MONTH(tr.transactionDate) = 5 THEN tr.totalAmount END), 0) AS May,
                    COALESCE(SUM(CASE WHEN MONTH(tr.transactionDate) = 6 THEN tr.totalAmount END), 0) AS Jun,
                    COALESCE(SUM(CASE WHEN MONTH(tr.transactionDate) = 7 THEN tr.totalAmount END), 0) AS Jul,
                    COALESCE(SUM(CASE WHEN MONTH(tr.transactionDate) = 8 THEN tr.totalAmount END), 0) AS Aug,
                    COALESCE(SUM(CASE WHEN MONTH(tr.transactionDate) = 9 THEN tr.totalAmount END), 0) AS Sep,
                    COALESCE(SUM(CASE WHEN MONTH(tr.transactionDate) = 10 THEN tr.totalAmount END), 0) AS Oct,
                    COALESCE(SUM(CASE WHEN MONTH(tr.transactionDate) = 11 THEN tr.totalAmount END), 0) AS Nov,
                    COALESCE(SUM(CASE WHEN MONTH(tr.transactionDate) = 12 THEN tr.totalAmount END), 0) AS `Dec` 
                FROM transactions tr
                INNER JOIN users u ON u.id = tr.cashierId
                WHERE YEAR(tr.transactionDate) = {singapore_year} 
                AND tr.branchId = {branch_id}
            """,
            "All": f"""
                WITH RECURSIVE MonthSeries AS (
                    SELECT DATE_FORMAT(MIN(transactionDate), '%Y-%m-01') AS monthStart 
                    FROM transactions 
                    WHERE branchId = {branch_id}
                    UNION ALL
                    SELECT DATE_ADD(monthStart, INTERVAL 1 MONTH) 
                    FROM MonthSeries
                    WHERE monthStart < (SELECT DATE_FORMAT(MAX(transactionDate), '%Y-%m-01') FROM transactions WHERE branchId = {branch_id})
                )
                SELECT 
                    DATE_FORMAT(ms.monthStart, '%b %Y') AS YearMonth,
                    COALESCE(SUM(tr.totalAmount), 0) AS TotalAmount
                FROM MonthSeries ms
                LEFT JOIN transactions tr 
                    ON DATE_FORMAT(tr.transactionDate, '%Y-%m') = DATE_FORMAT(ms.monthStart, '%Y-%m')
                    AND tr.branchId = {branch_id}
                GROUP BY ms.monthStart, YearMonth  
                ORDER BY ms.monthStart;
            """
        }
        
        sales_data = {}
        for filter_type, query in queries.items():
            result = await connection.execute_query_dict(query)
            if filter_type == "All":
                sales_data[filter_type] = [
                    {"label": row["YearMonth"], "value": float(row["TotalAmount"]), "dataPointText": f"₱{float(row['TotalAmount']):,.2f}"} for row in result
                ]
            else:
                sales_data[filter_type] = [
                    {"label": k.replace('_', ' '), "value": float(v), "dataPointText": f"₱{float(v):,.2f}" } for row in result for k, v in row.items()
                ]
        
        await websocket.send_json(sales_data)
        await asyncio.sleep(1)

async def analysisReport(websocket, branchId):
    while True:
        now_sg = datetime.now(timezone.utc) + timedelta(hours=8)
        connection = Tortoise.get_connection('default')
        singapore_year = now_sg.year
        singapore_month = now_sg.month

        percentQuery = f"""
            SELECT 
                CASE 
                    WHEN 
                        COUNT(DISTINCT CASE 
                            WHEN MONTH(transactionDate) <> {singapore_month} 
                            AND YEAR(transactionDate) <> {singapore_year} 
                            THEN DATE_FORMAT(transactionDate, '%Y-%m') 
                        END) > 0
                        AND 
                        SUM(CASE 
                            WHEN MONTH(transactionDate) <> {singapore_month} 
                            AND YEAR(transactionDate) <> {singapore_year} 
                            THEN totalAmount 
                        END) > 0 
                    THEN 
                        CAST((( 
                            SUM(CASE 
                                WHEN MONTH(transactionDate) = {singapore_month} 
                                AND YEAR(transactionDate) = {singapore_year} 
                                THEN totalAmount 
                            END) - 
                            (SUM(CASE 
                                WHEN MONTH(transactionDate) <> {singapore_month} 
                                AND YEAR(transactionDate) <> {singapore_year} 
                                THEN totalAmount 
                            END) / 
                            COUNT(DISTINCT CASE 
                                WHEN MONTH(transactionDate) <> {singapore_month} 
                                AND YEAR(transactionDate) <> {singapore_year} 
                                THEN DATE_FORMAT(transactionDate, '%Y-%m') 
                            END))
                        ) 
                        / 
                        (SUM(CASE 
                            WHEN MONTH(transactionDate) <> {singapore_month} 
                            AND YEAR(transactionDate) <> {singapore_year} 
                            THEN totalAmount 
                        END) / 
                        COUNT(DISTINCT CASE 
                            WHEN MONTH(transactionDate) <> {singapore_month} 
                            AND YEAR(transactionDate) <> {singapore_year} 
                            THEN DATE_FORMAT(transactionDate, '%Y-%m') 
                        END))
                    ) * 100 AS DOUBLE)
                    ELSE 0.0 
                END AS percentageChange
            FROM transactions
            INNER JOIN branches b ON b.Id = transactions.branchId
            WHERE b.id = {branchId};
        """

        percentage = await connection.execute_query_dict(percentQuery)

        highestSalesQuery = """
            SELECT 
                transactionDate AS highestSalesDate, 
                SUM(totalAmount) AS highestSalesAmount
            FROM transactions
            INNER JOIN branches b ON b.Id = transactions.branchId
            WHERE b.id = %s
            GROUP BY transactionDate
            ORDER BY highestSalesAmount DESC
            LIMIT 1
        """
        highestSales = await connection.execute_query_dict(highestSalesQuery, [branchId])

        highestSalesCurMonth = f"""
            SELECT 
                transactionDate AS highestSalesDate, 
                SUM(totalAmount) AS highestSalesAmount
            FROM transactions
            INNER JOIN branches b ON b.Id = transactions.branchId
            WHERE b.id = {branchId}
            AND MONTH(transactionDate) = {singapore_month} 
            AND YEAR(transactionDate) = {singapore_year}
            GROUP BY transactionDate
            ORDER BY highestSalesAmount DESC
            LIMIT 1;
        """
        highestSalesMonth = await connection.execute_query_dict(highestSalesCurMonth)

        highSmallQuery = f"""
            SELECT 
                COUNT(CASE WHEN totalAmount < 1500 THEN 1 END) AS smallOrderCount,
                COUNT(CASE WHEN totalAmount > 1500 THEN 1 END) AS highOrderCount,
                CASE 
                    WHEN COUNT(*) = 0 
                    THEN NULL 
                    ELSE 
                        CONCAT(
                            ROUND(
                                COUNT(CASE WHEN totalAmount < 1500 THEN 1 END) * 100.0 / COUNT(*), 2
                            ), '%'
                        ) 
                END AS smallOrderPercentage,
                CASE 
                    WHEN COUNT(*) = 0 
                    THEN NULL 
                    ELSE 
                        CONCAT(
                            ROUND(
                                COUNT(CASE WHEN totalAmount > 1500 THEN 1 END) * 100.0 / COUNT(*), 2
                            ), '%'
                        ) 
                END AS highOrderPercentage
            FROM transactions
            INNER JOIN branches b ON b.Id = transactions.branchId
            WHERE b.id = {branchId}
        """
        highSmallValue = await connection.execute_query_dict(highSmallQuery)

        peakQuery = """
            SELECT 
                CASE 
                    WHEN TIME(transactionDate) BETWEEN '07:00:00' AND '09:30:00' THEN '7-9:30 AM'
                    WHEN TIME(transactionDate) BETWEEN '09:31:00' AND '12:00:00' THEN '9:30-12:00 PM'
                    WHEN TIME(transactionDate) BETWEEN '12:01:00' AND '14:30:00' THEN '12:00-2:30 PM'
                    WHEN TIME(transactionDate) BETWEEN '14:31:00' AND '17:00:00' THEN '2:30-5:00 PM'
                    ELSE 'Other'
                END AS peakPeriod,
                COUNT(*) AS transactionCount
            FROM transactions
            INNER JOIN branches b ON b.Id = transactions.branchId
            WHERE b.id = %s
            GROUP BY peakPeriod
            ORDER BY transactionCount DESC
            LIMIT 1
        """
        peakValue = await connection.execute_query_dict(peakQuery, [branchId])

        response = {
            "percentChange": percentage[0]['percentageChange'] if percentage else 0.0,
            "highestSalesDate": highestSales[0]['highestSalesDate'] if highestSales else None,
            "highestSalesAmount": highestSales[0]['highestSalesAmount'] if highestSales else None,
            "highestSalesMonthDate": highestSalesMonth[0]['highestSalesDate'] if highestSalesMonth else None,
            "highestSalesMonthAmount": highestSalesMonth[0]['highestSalesAmount'] if highestSalesMonth else None,
            "smallOrderPercentage": highSmallValue[0]['smallOrderPercentage'] if highSmallValue else None,
            "highOrderPercentage": highSmallValue[0]['highOrderPercentage'] if highSmallValue else None,
            "peakPeriod": peakValue[0]['peakPeriod'] if peakValue else None,
        }

        await websocket.send_json(response)
        await asyncio.sleep(1)

async def analyticsDataHQ(websocket):
    while True:
        now_sg = datetime.now(timezone.utc) + timedelta(hours=8)
        connection = Tortoise.get_connection('default')
        singapore_year = now_sg.year
        singapore_month = now_sg.month
        singapore_date = now_sg.date()

        queries = {
            "Week": f"""
                SELECT 
                    COALESCE(SUM(CASE WHEN WEEKDAY(tr.transactionDate) = 0 THEN tr.totalAmount END), 0) AS Monday,
                    COALESCE(SUM(CASE WHEN WEEKDAY(tr.transactionDate) = 1 THEN tr.totalAmount END), 0) AS Tuesday,
                    COALESCE(SUM(CASE WHEN WEEKDAY(tr.transactionDate) = 2 THEN tr.totalAmount END), 0) AS Wednesday,
                    COALESCE(SUM(CASE WHEN WEEKDAY(tr.transactionDate) = 3 THEN tr.totalAmount END), 0) AS Thursday,
                    COALESCE(SUM(CASE WHEN WEEKDAY(tr.transactionDate) = 4 THEN tr.totalAmount END), 0) AS Friday,
                    COALESCE(SUM(CASE WHEN WEEKDAY(tr.transactionDate) = 5 THEN tr.totalAmount END), 0) AS Saturday
                FROM transactions tr
                INNER JOIN users u ON u.id = tr.cashierId
                WHERE DATE(tr.transactionDate) BETWEEN 
                    DATE_SUB('{singapore_date}', INTERVAL WEEKDAY('{singapore_date}') DAY) 
                    AND 
                    DATE_SUB('{singapore_date}', INTERVAL WEEKDAY('{singapore_date}') - 5 DAY)
            """,
            "Month": f"""
                SELECT 
                    COALESCE(SUM(CASE WHEN tr.transactionDate BETWEEN DATE_FORMAT('{singapore_date}', '%Y-%m-01') 
                                      AND DATE_ADD(DATE_FORMAT('{singapore_date}', '%Y-%m-01'), INTERVAL 6 DAY) THEN tr.totalAmount END), 0) AS Week_1,
                    COALESCE(SUM(CASE WHEN tr.transactionDate BETWEEN DATE_ADD(DATE_FORMAT('{singapore_date}', '%Y-%m-01'), INTERVAL 7 DAY) 
                                      AND DATE_ADD(DATE_FORMAT('{singapore_date}', '%Y-%m-01'), INTERVAL 13 DAY) THEN tr.totalAmount END), 0) AS Week_2,
                    COALESCE(SUM(CASE WHEN tr.transactionDate BETWEEN DATE_ADD(DATE_FORMAT('{singapore_date}', '%Y-%m-01'), INTERVAL 14 DAY) 
                                      AND DATE_ADD(DATE_FORMAT('{singapore_date}', '%Y-%m-01'), INTERVAL 20 DAY) THEN tr.totalAmount END), 0) AS Week_3,
                    COALESCE(SUM(CASE WHEN tr.transactionDate BETWEEN DATE_ADD(DATE_FORMAT('{singapore_date}', '%Y-%m-01'), INTERVAL 21 DAY) 
                                      AND LAST_DAY('{singapore_date}') THEN tr.totalAmount END), 0) AS Week_4
                FROM transactions tr
                WHERE MONTH(tr.transactionDate) = {singapore_month} AND YEAR(tr.transactionDate) = {singapore_year};
            """,
            "Year": f"""
                SELECT 
                    COALESCE(SUM(CASE WHEN MONTH(tr.transactionDate) = 1 THEN tr.totalAmount END), 0) AS Jan,
                    COALESCE(SUM(CASE WHEN MONTH(tr.transactionDate) = 2 THEN tr.totalAmount END), 0) AS Feb,
                    COALESCE(SUM(CASE WHEN MONTH(tr.transactionDate) = 3 THEN tr.totalAmount END), 0) AS Mar,
                    COALESCE(SUM(CASE WHEN MONTH(tr.transactionDate) = 4 THEN tr.totalAmount END), 0) AS Apr,
                    COALESCE(SUM(CASE WHEN MONTH(tr.transactionDate) = 5 THEN tr.totalAmount END), 0) AS May,
                    COALESCE(SUM(CASE WHEN MONTH(tr.transactionDate) = 6 THEN tr.totalAmount END), 0) AS Jun,
                    COALESCE(SUM(CASE WHEN MONTH(tr.transactionDate) = 7 THEN tr.totalAmount END), 0) AS Jul,
                    COALESCE(SUM(CASE WHEN MONTH(tr.transactionDate) = 8 THEN tr.totalAmount END), 0) AS Aug,
                    COALESCE(SUM(CASE WHEN MONTH(tr.transactionDate) = 9 THEN tr.totalAmount END), 0) AS Sep,
                    COALESCE(SUM(CASE WHEN MONTH(tr.transactionDate) = 10 THEN tr.totalAmount END), 0) AS Oct,
                    COALESCE(SUM(CASE WHEN MONTH(tr.transactionDate) = 11 THEN tr.totalAmount END), 0) AS Nov,
                    COALESCE(SUM(CASE WHEN MONTH(tr.transactionDate) = 12 THEN tr.totalAmount END), 0) AS `Dec` 
                FROM transactions tr
                INNER JOIN users u ON u.id = tr.cashierId
                WHERE YEAR(tr.transactionDate) = {singapore_year} 
            """,
            "All": f"""
                WITH RECURSIVE MonthSeries AS (
                    SELECT DATE_FORMAT(MIN(transactionDate), '%Y-%m-01') AS monthStart 
                    FROM transactions 
                    UNION ALL
                    SELECT DATE_ADD(monthStart, INTERVAL 1 MONTH) 
                    FROM MonthSeries
                    WHERE monthStart < (SELECT DATE_FORMAT(MAX(transactionDate), '%Y-%m-01') FROM transactions)
                )
                SELECT 
                    DATE_FORMAT(ms.monthStart, '%b %Y') AS YearMonth,
                    COALESCE(SUM(tr.totalAmount), 0) AS TotalAmount
                FROM MonthSeries ms
                LEFT JOIN transactions tr 
                    ON DATE_FORMAT(tr.transactionDate, '%Y-%m') = DATE_FORMAT(ms.monthStart, '%Y-%m')
                GROUP BY ms.monthStart, YearMonth  
                ORDER BY ms.monthStart;
            """
        }
        
        sales_data = {}
        for filter_type, query in queries.items():
            result = await connection.execute_query_dict(query)
            if filter_type == "All":
                sales_data[filter_type] = [
                    {"label": row["YearMonth"], "value": float(row["TotalAmount"]), "dataPointText": f"₱{float(row['TotalAmount']):,.2f}"} for row in result
                ]
            else:
                sales_data[filter_type] = [
                    {"label": k.replace('_', ' '), "value": float(v), "dataPointText": f"₱{float(v):,.2f}" } for row in result for k, v in row.items()
                ]
        
        await websocket.send_json(sales_data)
        await asyncio.sleep(1)

async def analysisReportHQ(websocket):
    while True:
        now_sg = datetime.now(timezone.utc) + timedelta(hours=8)
        connection = Tortoise.get_connection('default')
        singapore_year = now_sg.year
        singapore_month = now_sg.month

        percentQuery = f"""
            SELECT 
                CASE 
                    WHEN 
                        COUNT(DISTINCT CASE 
                            WHEN MONTH(transactionDate) <> {singapore_month} 
                            AND YEAR(transactionDate) <> {singapore_year} 
                            THEN DATE_FORMAT(transactionDate, '%Y-%m') 
                        END) > 0
                        AND 
                        SUM(CASE 
                            WHEN MONTH(transactionDate) <> {singapore_month} 
                            AND YEAR(transactionDate) <> {singapore_year} 
                            THEN totalAmount 
                        END) > 0 
                    THEN 
                        CAST((( 
                            SUM(CASE 
                                WHEN MONTH(transactionDate) = {singapore_month} 
                                AND YEAR(transactionDate) = {singapore_year} 
                                THEN totalAmount 
                            END) - 
                            (SUM(CASE 
                                WHEN MONTH(transactionDate) <> {singapore_month} 
                                AND YEAR(transactionDate) <> {singapore_year} 
                                THEN totalAmount 
                            END) / 
                            COUNT(DISTINCT CASE 
                                WHEN MONTH(transactionDate) <> {singapore_month} 
                                AND YEAR(transactionDate) <> {singapore_year} 
                                THEN DATE_FORMAT(transactionDate, '%Y-%m') 
                            END))
                        ) 
                        / 
                        (SUM(CASE 
                            WHEN MONTH(transactionDate) <> {singapore_month} 
                            AND YEAR(transactionDate) <> {singapore_year} 
                            THEN totalAmount 
                        END) / 
                        COUNT(DISTINCT CASE 
                            WHEN MONTH(transactionDate) <> {singapore_month} 
                            AND YEAR(transactionDate) <> {singapore_year} 
                            THEN DATE_FORMAT(transactionDate, '%Y-%m') 
                        END))
                    ) * 100 AS DOUBLE)
                    ELSE 0.0 
                END AS percentageChange
            FROM transactions
        """

        percentage = await connection.execute_query_dict(percentQuery)

        highestSalesQuery = """
            SELECT 
                transactionDate AS highestSalesDate, 
                SUM(totalAmount) AS highestSalesAmount
            FROM transactions
            GROUP BY transactionDate
            ORDER BY highestSalesAmount DESC
            LIMIT 1
        """
        highestSales = await connection.execute_query_dict(highestSalesQuery)

        highestSalesCurMonth = f"""
            SELECT 
                transactionDate AS highestSalesDate, 
                SUM(totalAmount) AS highestSalesAmount
            FROM transactions
            WHERE MONTH(transactionDate) = {singapore_month} 
            AND YEAR(transactionDate) = {singapore_year}
            GROUP BY transactionDate
            ORDER BY highestSalesAmount DESC
            LIMIT 1;
        """
        highestSalesMonth = await connection.execute_query_dict(highestSalesCurMonth)

        highSmallQuery = f"""
            SELECT 
                COUNT(CASE WHEN totalAmount < 1500 THEN 1 END) AS smallOrderCount,
                COUNT(CASE WHEN totalAmount > 1500 THEN 1 END) AS highOrderCount,
                CASE 
                    WHEN COUNT(*) = 0 
                    THEN NULL 
                    ELSE 
                        CONCAT(
                            ROUND(
                                COUNT(CASE WHEN totalAmount < 1500 THEN 1 END) * 100.0 / COUNT(*), 2
                            ), '%'
                        ) 
                END AS smallOrderPercentage,
                CASE 
                    WHEN COUNT(*) = 0 
                    THEN NULL 
                    ELSE 
                        CONCAT(
                            ROUND(
                                COUNT(CASE WHEN totalAmount > 1500 THEN 1 END) * 100.0 / COUNT(*), 2
                            ), '%'
                        ) 
                END AS highOrderPercentage
            FROM transactions
        """
        highSmallValue = await connection.execute_query_dict(highSmallQuery)

        peakQuery = """
            SELECT 
                CASE 
                    WHEN TIME(transactionDate) BETWEEN '07:00:00' AND '09:30:00' THEN '7-9:30 AM'
                    WHEN TIME(transactionDate) BETWEEN '09:31:00' AND '12:00:00' THEN '9:30-12:00 PM'
                    WHEN TIME(transactionDate) BETWEEN '12:01:00' AND '14:30:00' THEN '12:00-2:30 PM'
                    WHEN TIME(transactionDate) BETWEEN '14:31:00' AND '17:00:00' THEN '2:30-5:00 PM'
                    ELSE 'Other'
                END AS peakPeriod,
                COUNT(*) AS transactionCount
            FROM transactions
            GROUP BY peakPeriod
            ORDER BY transactionCount DESC
            LIMIT 1
        """
        peakValue = await connection.execute_query_dict(peakQuery)

        response = {
            "percentChange": percentage[0]['percentageChange'] if percentage else 0.0,
            "highestSalesDate": highestSales[0]['highestSalesDate'] if highestSales else None,
            "highestSalesAmount": highestSales[0]['highestSalesAmount'] if highestSales else None,
            "highestSalesMonthDate": highestSalesMonth[0]['highestSalesDate'] if highestSalesMonth else None,
            "highestSalesMonthAmount": highestSalesMonth[0]['highestSalesAmount'] if highestSalesMonth else None,
            "smallOrderPercentage": highSmallValue[0]['smallOrderPercentage'] if highSmallValue else None,
            "highOrderPercentage": highSmallValue[0]['highOrderPercentage'] if highSmallValue else None,
            "peakPeriod": peakValue[0]['peakPeriod'] if peakValue else None,
        }

        await websocket.send_json(response)
        await asyncio.sleep(1)
