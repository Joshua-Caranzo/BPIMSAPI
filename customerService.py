from models import Customer, Branch, Transaction, Cart, ItemReward, LoyaltyCard, LoyaltyCustomer, LoyaltyStages, TransactionItem, Item, BranchItem
from utils import create_response, upload_media, delete_media
import os
from tortoise.queryset import Q 
from datetime import date
from tortoise import Tortoise
from decimal import Decimal

async def getCustomerList(branchId = None, search = ""):

    customer_query = Customer.all().order_by('name')

    if branchId:
        customer_query = customer_query.filter(
            Q(branchId=branchId) | Q(branchId__isnull=True)
        )
        
    if search:
        customer_query = customer_query.filter(Q(name__icontains=search))

    customers = await customer_query.values("id", "name", "branchId")

    return create_response(True, "Customer list retrieved successfully.", customers, None), 200

async def getCustomer(id):
    if id:
        customer = await Customer.get_or_none(id=id)

        if customer:
            branch = await Branch.get_or_none(id=customer.branchId)

            query = """
                SELECT tr.id, tr.amountReceived, tr.totalAmount, tr.slipNo, tr.transactionDate, tr.isVoided, u.name as cashier 
                FROM transactions tr 
                INNER JOIN users u ON u.id = tr.cashierId
                WHERE customerId = %s
            """

            transactions = await Tortoise.get_connection("default").execute_query_dict(query, [id])

            orderHistory = []
            for transaction in transactions:
                transactionItems = await TransactionItem.filter(transactionId=transaction["id"])
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

                orderHistory.append({
                    "id": transaction['id'],
                    "totalAmount": transaction['totalAmount'],
                    "amountReceived": transaction['amountReceived'],
                    "slipNo": transaction['slipNo'],
                    "transactionDate": transaction['transactionDate'],
                    "isVoided": transaction['isVoided'],
                    "cashier": transaction['cashier'],
                    "items": items
                })

            customer_data = {
                "id": customer.id,
                "name": customer.name,
                "contactNumber1": customer.contactNumber1,
                "contactNumber2": customer.contactNumber2,
                "totalOrderAmount": customer.totalOrderAmount,
                "branchId": customer.branchId,
                "branch": branch.name if branch else None,
                "fileName": customer.fileName,
                "isLoyalty": customer.isLoyalty
            }

            request = {
                "customer": customer_data,
                "orderHistory": orderHistory
            }

            message = "Customer successfully retrieved"
        else:
            request = None
            message = "Customer not found"
    else:
        request = None
        message = "No Customers Retrieved"

    return create_response(True, message, request, None), 200

async def saveCustomer(data, file):
    customerId = int(data.get('id'))
    name = data.get('name')
    contactNumber1 = data.get('contactNumber1')
    contactNumber2 = data.get('contactNumber2')
    branchId = data.get('branchId')

    if customerId == 0:
        customer = await Customer.create(
            branchId=branchId,
            contactNumber1=contactNumber1,
            contactNumber2=contactNumber2,
            totalOrderAmount= 0.00,
            name = name,
            isLoyalty = False
        )
        customerId = customer.id
        message = "Customer added successfully."
    else: 
        existing_customer = await Customer.get_or_none(id=customerId)
        if not existing_customer:
            return create_response(False, "Customer not found.", None, None), 404

        existing_customer.contactNumber1 = contactNumber1
        existing_customer.contactNumber2 = contactNumber2
        existing_customer.name = name
        if branchId:
            existing_customer.branchId = branchId
        await existing_customer.save()

        message = "Customer updated successfully."

    if(file != None):
            result = upload_media(file)
            existing_customer = await Customer.get_or_none(id=customerId)
            existing_customer.fileName = result["secure_url"]
            existing_customer.imageId = result["public_id"]
            await existing_customer.save()

    return create_response(True, message, customerId, None), 200

async def deleteCustomer(id):
    customer = await Customer.get_or_none(id=id)
    
    if not customer:
        return create_response(False, "Customer not found.", None, None), 200

    if customer.fileName:
        response = delete_media(customer.imageId)
        if(response == False):
            return create_response(False, "An error occured.", None, None), 200
        
    carts = await Cart.filter(customerId=id)

    transactions = await Transaction.filter(customerId=id)

    for cart in carts:
        cart.customerId = None
        await cart.save()

    for transaction in transactions:
        transaction.customerId = None
        await transaction.save()

    await customer.delete()

    return create_response(True, "Customer deleted successfully.", None, None), 200

async def saveItemsReward(id, name):
    if id == 0:
        await ItemReward.create(
            name=name
        )
        message = "Reward added successfully."
    else: 
        existing_reward = await ItemReward.get_or_none(id=id)
        if not existing_reward:
            return create_response(False, "Reward not found.", None, None), 404

        existing_reward.name = name
        await existing_reward.save()

        message = "Reward updated successfully."

    return create_response(True, message, None, None), 200

async def saveLoyaltyCard(card):
    cardId = 0
    if card['id'] == 0:
        savedCard = await LoyaltyCard.create(
            validYear=card['validYear'],
            isValid = card['isValid']
        )
        cardId = savedCard.id
        message = "Card added successfully."
    else: 
        existingCard = await LoyaltyCard.get_or_none(id=card['id'])
        if not existingCard:
            return create_response(False, "Card not found.", None, None), 404

        existingCard.validYear = card['validYear']
        existingCard.isValid = card['isValid']
        cardId = existingCard.id
        await existingCard.save()

        message = "Card updated successfully."

    if(card['isValid'] == True):
        cards = await LoyaltyCard.filter(id!=cardId)
        for card in cards:
            card.isValid = False
       
    return create_response(True, message, None, None), 200

async def saveLoyaltyStage(stage):
    if stage['itemRewardId'] == 0 :
        stage['itemRewardId'] = None

    if stage['id'] == 0:
        loyaltyStage = await LoyaltyStages.create(
            loyaltyCardId=stage['loyaltyCardId'],
            orderId = stage['orderId'],
            itemRewardId=stage['itemRewardId']
        )

        customers = await Customer.filter(isLoyalty = True)

        for customer in customers:
            await LoyaltyCustomer.create(
                customerId = customer.id,
                stageId = loyaltyStage.id,
                isDone = False,
                dateDone = None,
                itemId = None
            )

        message = "Stage added successfully."
    else: 
        existingStage = await LoyaltyStages.get_or_none(id=stage['id'])
        if not existingStage:
            return create_response(False, "Card not found.", None, None), 404

        existingStage.loyaltyCardId = stage['loyaltyCardId']
        existingStage.orderId = stage['orderId']
        existingStage.itemRewardId = stage['itemRewardId']
        await existingStage.save()

        message = "Stage updated successfully."

    return create_response(True, message, None, None), 200


async def saveLoyaltyCustomer(customerId):

    card = await LoyaltyCard.get_or_none(isValid=True)

    stages = await LoyaltyStages.filter(loyaltyCardId = card.id)

    for stage in stages:
        isDone = stage.orderId == 1 or False
        dateDone = date.today() if isDone else None
        await LoyaltyCustomer.create(
            customerId = customerId,
            stageId = stage.id,
            isDone = isDone,
            dateDone = dateDone,
            itemId = None
        )

    return create_response(True, "Creation of Loyalty Saved Succesfully", None, None), 200

async def markNextStageDone(customerId):
    query = """
        SELECT lc.id AS loyalty_customer_id, lc.stageId, lc.isDone, ls.orderId
        FROM loyaltycustomers lc
        JOIN loyaltyStages ls ON lc.stageId = ls.id
        WHERE lc.customerId = %s
        ORDER BY ls.orderId ASC
    """

    customerStages = await Tortoise.get_connection("default").execute_query_dict(query, [customerId])
    
    if not customerStages:
        return create_response(False, "No stages found for customer.", None, None), 400

    latest_stage = None
    for stage in customerStages:
        if stage["isDone"]:
            latest_stage = stage

    if not latest_stage:
        return False

    if latest_stage["orderId"] == customerStages[-1]["orderId"]:
        return True

    next_stage = None
    for stage in customerStages:
        if stage["orderId"] > latest_stage["orderId"] and not stage["isDone"]:
            next_stage = stage
            break

    if next_stage:
        await LoyaltyCustomer.filter(id=next_stage["loyalty_customer_id"]).update(
            isDone=True,
            dateDone=date.today()
        )

        return False
    
    return False

async def getLoyaltyCardList():
    card_query = LoyaltyCard.all().order_by('isValid', 'id')

    cards = await card_query.values("id", "validYear", "isValid")

    return create_response(True, "Card list retrieved successfully.", cards, None), 200

async def getLoyaltyStages(cardId):

    sqlQuery = """
        SELECT ls.id, ls.orderId, ls.loyaltyCardId, ls.itemRewardId, ir.name as rewardName from loyaltyStages ls 
        LEFT JOIN itemRewards ir on ir.Id = ls.itemRewardId
        WHERE ls.loyaltyCardId = %s
        ORDER BY ls.orderId
        """
    params = [cardId]

    connection = Tortoise.get_connection('default')
    result = await connection.execute_query(sqlQuery, tuple(params))

    stages = result[1]

    stageList = [
        {
            "id": h['id'],
            "orderId": h['orderId'],
            "loyaltyCardId": h['loyaltyCardId'],
            "itemRewardId": h['itemRewardId'],
            "rewardName": h['rewardName']
        }
        for h in stages
    ]

    return create_response(True, "Success", stageList, None), 200

async def getRewards():
    reward_query = ItemReward.all().order_by('name')

    rewards = await reward_query.values("id", "name")

    return create_response(True, "Rewards list retrieved successfully.", rewards, None), 200

async def getCustomerLoyalty(customerId):

    customer  = await Customer.get_or_none(id = customerId)
    if customer.isLoyalty == False:
        return create_response(False, "Customer is not member", None, None), 200    
    
    sqlQuery = """
        SELECT lc.*, ls.itemRewardId, r.name, l.validYear, ls.orderId, i.name itemName
        from loyaltycustomers lc
        inner join loyaltystages ls on ls.id = lc.stageId
        LEFT JOIN itemrewards r on r.id = ls.itemRewardId
        INNER JOIN loyaltycards l on l.id = ls.loyaltyCardId
        left join branchitem bi on bi.id = lc.itemId
		LEFT JOIN items i on bi.itemId = i.id
        where customerId = %s AND l.isValid = 1
        ORDER BY ls.orderId
        """
    
    params = [customerId]

    connection = Tortoise.get_connection('default')
    result = await connection.execute_query(sqlQuery, tuple(params))

    stages = result[1]

    stageList = [
        {
            "id": h['id'],
            "customerId": h['customerId'],
            "stageId": h['stageId'],
            "isDone": h['isDone'],
            "dateDone": h['dateDone'],
            "itemId": h['itemId'],
            "itemRewardId": h['itemRewardId'],
            "name": h['name'],
            "validYear": h['validYear'],
            "orderId": h['orderId'],
            "itemName": h['itemName']
        }
        for h in stages
    ]

    return create_response(True, "Success", stageList, None), 200

async def saveCustomerItemReward(id, itemId, branchId, qty):

    loyaltyCustomer = await LoyaltyCustomer.get_or_none(id=id)
    branchItem = await BranchItem.get_or_none(itemId = itemId, branchId = branchId)

    loyaltyCustomer.itemId = branchItem.id
    branchItem.quantity -= Decimal(qty)

    await loyaltyCustomer.save()
    await branchItem.save()

    return create_response(True, "Picked Item Successfully", None, None), 200

async def changeReward(id, itemId, branchId, lastItemId, qty, lastQty):

    loyaltyCustomer = await LoyaltyCustomer.get_or_none(id=id)
    lastItem = await BranchItem.get_or_none(itemId = lastItemId, branchId = branchId) 
    branchItem = await BranchItem.get_or_none(itemId = itemId, branchId = branchId)

    loyaltyCustomer.itemId = branchItem.id
    branchItem.quantity -= Decimal(qty)
    lastItem.quantity += Decimal(lastQty)
    await loyaltyCustomer.save()
    await branchItem.save()
    await lastItem.save()

    return create_response(True, "Picked Item Successfully", None, None), 200