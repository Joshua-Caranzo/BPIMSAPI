from quart import Quart, request, send_file, websocket, send_from_directory
from tortoise import Tortoise
import userService
import itemService
import categoryService
import transactionService
import customerService
import fileService
import socketService
import warehouseService
import stockService
import centralService
from db import DATABASE_CONFIG
import asyncio
import uvicorn
from quart_cors  import cors
from utils import token_required
from config import CUSTOMER_IMAGES, ITEM_IMAGES
import os

app = Quart(__name__)
cors(app)

async def init():
    try:
        await Tortoise.init(config=DATABASE_CONFIG)
    except ConnectionError as e:
        print(f"Database configuration error: {e}")

@app.before_serving
async def startup():
    await init()

""" GET METHODS """        

@app.route('/getProducts', methods=['GET'])
@token_required
async def get_products():
    categoryId = request.args.get('categoryId')
    page = request.args.get('page')
    search = request.args.get('search')
    branchId = request.args.get('branchId')
    response = await itemService.get_products(int(categoryId), int(branchId), int(page), search) 
    return response

@app.route('/getCategories', methods=['GET'])
@token_required
async def get_categories():
    response = await categoryService.get_categories() 
    return response

@app.route('/getCustomerList', methods=['GET'])
@token_required
async def getCustomerList():
    branchId = request.args.get('branchid')
    search = request.args.get('search')
    if branchId is not None:
        branchId = int(branchId) if branchId.isdigit() else None
    response = await customerService.getCustomerList(branchId, search)
    
    return response

@app.route('/getCustomer', methods=['GET'])
@token_required
async def getCustomer():
    id = request.args.get('id')
    response = await customerService.getCustomer(int(id)) 
    return response

@app.route('/getCart', methods=['GET'])
@token_required
async def getCartandItems():
    userId = request.user_id
    response = await transactionService.getCartandItems(int(userId)) 
    return response

@app.route('/getBranchStocks', methods=['GET'])
@token_required
async def getBranchStocks():
    categoryId = request.args.get('categoryId')
    page = request.args.get('page')
    search = request.args.get('search')
    branchId = request.args.get('branchId')
    response = await itemService.getBranchStocks(int(categoryId), int(branchId), int(page), search) 
    return response

@app.route('/getStockHistory', methods=['GET'])
@token_required
async def getStockHistory():
    id = request.args.get('branchItemId')
    response = await itemService.getStockHistory(id) 
    return response

@app.route('/getCustomerImage', methods=['GET'])
async def getCustomerImage():
    fileName = request.args.get('fileName')
    if not fileName:
        return {"error": "fileName parameter is required"}, 400

    file_path = os.path.join(CUSTOMER_IMAGES, fileName)

    if not os.path.exists(file_path):
        return {"error": "File not found"}, 404

    return await send_file(file_path)

@app.route('/getUsers', methods=['GET'])
@token_required
async def getUsers():
    search = request.args.get('search')
    response = await userService.getUsers(search) 
    return response

@app.route('/getUser', methods=['GET'])
@token_required
async def getUser():
    id = request.args.get('id')
    response = await userService.getUserById(id) 
    return response

@app.route('/getDepartments', methods=['GET'])
@token_required
async def getDepartments():
    response = await userService.getDepartments() 
    return response

@app.route('/getBranches', methods=['GET'])
@token_required
async def getBranches():
    response = await userService.getBranches() 
    return response

@app.route('/getProductsHQ', methods=['GET'])
@token_required
async def getProductsHQ():
    categoryId = request.args.get('categoryId')
    page = request.args.get('page')
    search = request.args.get('search')
    response = await itemService.getProductsHQ(int(categoryId), int(page), search) 
    return response

@app.route('/getCategoriesHQ', methods=['GET'])
@token_required
async def getCategoriesHQ():
    response = await categoryService.getCategoriesHQ() 
    return response

@app.route('/getProductHQ', methods=['GET'])
@token_required
async def getProductHQ():
    itemId = request.args.get('id')
    response = await itemService.getProductHQ(itemId) 
    return response

@app.route('/getItemImage', methods=['GET'])
async def getItemImage():
    fileName = request.args.get('fileName')
    if not fileName:
        return {"error": "fileName parameter is required"}, 400

    file_path = os.path.join(ITEM_IMAGES, fileName)

    if not os.path.exists(file_path):
        return {"error": "File not found"}, 404

    return await send_file(file_path)

@app.route('/getStocksMonitor', methods=['GET'])
@token_required
async def getStocksMonitor():
    categoryId = request.args.get('categoryId')
    page = request.args.get('page')
    search = request.args.get('search')
    response = await itemService.getStocksMonitor(int(categoryId), int(page), search) 
    return response

@app.route('/getWHStocksMonitor', methods=['GET'])
@token_required
async def getWHStocksMonitor():
    categoryId = request.args.get('categoryId')
    page = request.args.get('page')
    search = request.args.get('search')
    response = await itemService.getWHStocksMonitor(int(categoryId), int(page), search) 
    return response

@app.route('/getTransactionHistory', methods=['GET'])
@token_required
async def getTransactionHistory():
    transactionId = request.args.get('transactionId')
    response = await transactionService.getTransactionHistory(int(transactionId)) 
    return response

@app.route('/getWHStocks', methods=['GET'])
@token_required
async def getWHStocks():
    categoryId = request.args.get('categoryId')
    page = request.args.get('page')
    search = request.args.get('search')
    response = await warehouseService.getWHStocks(int(categoryId), int(page), search) 
    return response

@app.route('/getWHStockHistory', methods=['GET'])
@token_required
async def getWHStockHistory():
    id = request.args.get('itemId')
    response = await warehouseService.getStockHistory(id) 
    return response

@app.route('/getSupplierStockHistory', methods=['GET'])
@token_required
async def getSupplierStockHistory():
    id = request.args.get('supplierId')
    response = await warehouseService.getSupplierStockHistory(id) 
    return response

@app.route('/getAllTransactions', methods=['GET'])
@token_required
async def getAllTransactionsAsync():
    branchId = request.args.get('branchId')
    page = request.args.get('page')
    search = request.args.get('search')
    response = await transactionService.getAllTransactionsAsync(int(branchId), int(page), search) 
    return response

@app.route('/getAllCentralTransactions', methods=['GET'])
@token_required
async def getAllCentralTransactionsAsync():
    page = request.args.get('page')
    search = request.args.get('search')
    categoryId = request.args.get('categoryId')

    response = await centralService.getAllCentralTransactionsAsync(categoryId, int(page), search) 
    return response

@app.route('/getAllTransactionsHQ', methods=['GET'])
@token_required
async def getAllTransactionsAsyncHQ():
    branchId = request.args.get('branchId')
    page = request.args.get('page')
    search = request.args.get('search')
    response = await transactionService.getAllTransactionsAsyncHQ(branchId, int(page), search) 
    return response

@app.route('/getSupplierList', methods=['GET'])
@token_required
async def getSupplierList():  
    search = request.args.get('search')
    response = await warehouseService.getSupplierList(search) 
    return response

@app.route('/getSupplier', methods=['GET'])
@token_required
async def getSupplier():  
    id = request.args.get('id')
    response = await warehouseService.getSupplier(int(id)) 
    return response

@app.route('/getBranchTransferHistory', methods=['GET'])
@token_required
async def getBranchTransferHistory():  
    id = request.args.get('branchItemId')
    response = await stockService.getBranchTransferHistory(int(id)) 
    return response

@app.route('/getReturnToStockHistory', methods=['GET'])
@token_required
async def getReturnToStockHistory():  
    id = request.args.get('whItemId')
    response = await warehouseService.getReturnToStockHistory(int(id)) 
    return response

@app.route('/getBranchReturnHistory', methods=['GET'])
@token_required
async def getBranchReturnHistory():  
    id = request.args.get('branchItemId')
    response = await stockService.getBranchReturnHistory(int(id)) 
    return response

@app.route('/getLoyaltyCardList', methods=['GET'])
@token_required
async def getLoyaltyCardList():  
    response = await customerService.getLoyaltyCardList() 
    return response

@app.route('/getLoyaltyStages', methods=['GET'])
@token_required
async def getLoyaltyStages():  
    cardId = request.args.get('cardId')
    response = await customerService.getLoyaltyStages(cardId) 
    return response

@app.route('/getRewards', methods=['GET'])
@token_required
async def getRewards():  
    response = await customerService.getRewards() 
    return response

@app.route('/getCustomerLoyalty', methods=['GET'])
@token_required
async def getCustomerLoyalty(): 
    customerId = request.args.get('customerId') 
    response = await customerService.getCustomerLoyalty(customerId) 
    return response

@app.route('/getCentralProducts', methods=['GET'])
@token_required
async def getCentralProducts(): 
    categoryId = request.args.get('categoryId')
    page = request.args.get('page')
    search = request.args.get('search')
    response = await centralService.getCentralProducts(int(categoryId), int(page), search) 
    return response

@app.route('/getOldestTransaction', methods=['GET'])
@token_required
async def getOldestTransaction(): 
    branchId = request.args.get('branchId')
    response = await transactionService.getOldestTransaction(int(branchId)) 
    return response

""" POST AND PUT METHODS """

@app.route('/loginUser', methods=['POST'])
async def login_user_route():
    data = await request.json
    response = await userService.login_user(data.get('email'), data.get('encryptedPassword')) 
    return response

@app.route('/deleteAllCartItems', methods=['PUT'])
@token_required
async def deleteAllCartItems():
    cart_Id = request.cart_id
    response = await transactionService.deleteAllCartItems(int(cart_Id)) 
    return response

@app.route('/removeCartItem', methods=['PUT'])
@token_required
async def removeCartItem():
    data = await request.json
    response = await transactionService.removeCartItem(int(data.get('cartItemId'))) 
    return response

@app.route('/updateItemQuantity', methods=['PUT'])
@token_required
async def updateItemQuantity():
    data = await request.json
    response = await transactionService.updateItemQuantity(int(data.get('cartItemId')), data.get('quantity')) 
    return response

@app.route('/updateDeliveryFee', methods=['PUT'])
@token_required
async def updateDeliveryFee():
    data = await request.json
    deliveryFee = data.get('deliveryFee')

    if deliveryFee is not None:
        deliveryFee = float(deliveryFee)
    else:
        deliveryFee = None 

    response = await transactionService.updateDeliveryFee(int(request.cart_id), deliveryFee
                                                   ) 
    return response

@app.route('/updateDiscount', methods=['PUT'])
@token_required
async def updateDiscount():
    data = await request.json
    discount = data.get('discount')

    if discount is not None:
        discount = float(discount)
    else:
        discount = None 

    response = await transactionService.updateDiscount(int(request.cart_id), discount) 
    return response

@app.route('/processPayment', methods=['POST'])
@token_required
async def processPayment():
    data = await request.json
    amountReceived = data.get('amountReceived')

    response = await transactionService.processPayment(int(request.cart_id), float(amountReceived)) 
    return response

@app.route('/processCentralPayment', methods=['POST'])
@token_required
async def processCentralPayment():
    data = await request.json
    amountReceived = data.get('amountReceived')
    isCredit = data.get('isCredit')
    response = await centralService.processCentralPayment(int(request.cart_id), float(amountReceived), bool(isCredit)) 
    return response

@app.route('/updateCustomer', methods=['PUT'])
@token_required
async def updateCustomer():
    data = await request.json
    id = data.get('id')

    response = await transactionService.updateCustomer(int(request.cart_id), id) 
    return response

@app.route('/generateReceipt', methods=['POST'])
@token_required
async def generate_pdf():
    data = await request.json
    transactionId = data.get('transactionId')

    pdf_buffer = await fileService.generateReceipt(transactionId) 

    return await send_file(pdf_buffer, as_attachment=True, mimetype='application/pdf')  

@app.route('/generateSalespdf', methods=['POST'])
@token_required
async def generateSalespdf():
    data = await request.json
    fromDate = data.get('fromDate')
    toDate = data.get('toDate')
    branchId = data.get('branchId')

    pdf_buffer = await fileService.generateSalesReport(fromDate,toDate, int(branchId)) 

    return await send_file(pdf_buffer, as_attachment=True, mimetype='application/pdf')  

@app.route('/saveCustomer', methods=['PUT'])
@token_required
async def saveCustomer():
    data = await request.form
    files = await request.files  
    file = files.get('file')
    response = await customerService.saveCustomer(data, file) 
    return response

@app.route('/deleteCustomer', methods=['PUT'])
@token_required
async def deleteCustomer():
    data = await request.json
    id = data.get('id')
    response = await customerService.deleteCustomer(int(id)) 
    return response

@app.route('/createStockInput', methods=['POST'])
@token_required
async def createStockInput():
    data = await request.json
    stockInput = data.get('stockInput')
    response = await itemService.createStockInput(stockInput) 
    return response

@app.route('/addUser', methods=['POST'])
@token_required
async def addUser():
    data = await request.json
    user = data.get('user')
    response = await userService.addUser(user) 
    return response

@app.route('/editUser', methods=['PUT'])
@token_required
async def editUser():
    data = await request.json
    user = data.get('user')
    response = await userService.editUser(user) 
    return response

@app.route('/saveItem', methods=['PUT'])
@token_required
async def saveItem():
    data = await request.form
    files = await request.files  
    file = files.get('file')
    response = await itemService.saveItem(data, file) 
    return response

@app.route('/deleteItem', methods=['PUT'])
@token_required
async def deleteItem():
    data = await request.json
    id = data.get('id')
    response = await itemService.deleteItem(int(id)) 
    return response

@app.route('/createWHStockInput', methods=['POST'])
@token_required
async def createWHStockInput():
    data = await request.json
    stockInput = data.get('stockInput')
    response = await warehouseService.createStockInput(stockInput) 
    return response

@app.route('/setUserInactive', methods=['POST'])
@token_required
async def setUserInactive():
    data = await request.json
    id = data.get('id')
    response = await userService.setInactiveUser(id) 
    return response

@app.route('/saveSupplier', methods=['POST'])
@token_required
async def saveSupplier():
    data = await request.json
    supplier = data.get('supplier')
    response = await warehouseService.saveSupplier(supplier) 
    return response

@app.route('/removeSupplier', methods=['POST'])
@token_required
async def removeSupplier():
    data = await request.json
    id = data.get('id')
    response = await warehouseService.removeSupplier(id) 
    return response

@app.route('/editStock', methods=['PUT'])
@token_required
async def editStock():
    data = await request.json
    id = data.get('id')
    qty = data.get('qty')
    response = await itemService.editStock(int(id), qty) 
    return response

@app.route('/editWHStock', methods=['PUT'])
@token_required
async def editWHStock():
    data = await request.json
    id = data.get('id')
    qty = data.get('qty')
    response = await warehouseService.editWHStock(int(id), qty) 
    return response

@app.route('/voidTransaction', methods=['PUT'])
@token_required
async def voidTransaction():
    data = await request.json
    id = data.get('id')
    response = await transactionService.voidTransaction(int(id)) 
    return response

@app.route('/saveBranchTransfer', methods=['POST'])
@token_required
async def saveBranchTransfer():
    data = await request.json
    branchTransfer = data.get('branchTransfer')
    response = await stockService.saveBranchTransfer(branchTransfer) 
    return response

@app.route('/returnToSupplier', methods=['POST'])
@token_required
async def returnToSupplier():
    data = await request.json
    returnStock = data.get('returnStock')
    response = await warehouseService.returnToSupplier(returnStock) 
    return response

@app.route('/returnToWH', methods=['POST'])
@token_required
async def returnToWH():
    data = await request.json
    returnStock = data.get('returnStock')
    response = await stockService.returnToWH(returnStock) 
    return response

@app.route('/setBranchInactive', methods=['PUT'])
@token_required
async def setBranchInactive():
    data = await request.json
    id = data.get('id')
    response = await userService.setBranchInactive(id) 
    return response

@app.route('/saveBranch', methods=['PUT'])
@token_required
async def saveBranch():
    data = await request.json
    id = data.get('id')
    name = data.get('name') 
    response = await userService.saveBranch(id, name) 
    return response

@app.route('/saveItemsReward', methods=['PUT'])
@token_required
async def saveItemsReward():
    data = await request.json
    id = data.get('id')
    name = data.get('name') 
    response = await customerService.saveItemsReward(id, name) 
    return response

@app.route('/saveLoyaltyCard', methods=['PUT'])
@token_required
async def saveLoyaltyCard():
    data = await request.json
    card = data.get('card')
    response = await customerService.saveLoyaltyCard(card) 
    return response

@app.route('/saveLoyaltyStage', methods=['PUT'])
@token_required
async def saveLoyaltyStage():
    data = await request.json
    stage = data.get('stage')
    response = await customerService.saveLoyaltyStage(stage) 
    return response

@app.route('/saveLoyaltyCustomer', methods=['PUT'])
@token_required
async def saveLoyaltyCustomer():
    data = await request.json
    customerId = data.get('customerId')
    response = await customerService.saveLoyaltyCustomer(customerId) 
    return response

@app.route('/markStageDone', methods=['PUT'])
@token_required
async def markStageDone():
    data = await request.json
    loyaltyCustomerId = data.get('loyaltyCustomerId')
    itemId = data.get('itemId')
    response = await customerService.markStageDone(loyaltyCustomerId, itemId) 
    return response

@app.route('/saveCustomerItemReward', methods=['PUT'])
@token_required
async def saveCustomerItemReward():
    data = await request.json
    id = data.get('id')
    itemId = data.get('itemId') 
    branchId = data.get('branchId')
    qty = data.get('qty')
    response = await customerService.saveCustomerItemReward(id, itemId, branchId, qty) 
    return response

@app.route('/changeReward', methods=['PUT'])
@token_required
async def changeReward():
    data = await request.json
    id = data.get('id')
    itemId = data.get('itemId') 
    branchId = data.get('branchId')
    lastItemId = data.get('lastItemId')
    qty = data.get('qty')
    lastQty = data.get('lastQty')
    response = await customerService.changeReward(id, itemId, branchId, lastItemId, qty, lastQty) 
    return response

@app.route('/addItemToCart', methods=['POST'])
@token_required
async def addItemToCart():
    data = await request.json
    response = await transactionService.addItemToCart(int(request.cart_id), int(data.get('itemId')), data.get('quantity')) 
    return response

@app.route('/addCentralItemToCart', methods=['POST'])
@token_required
async def addCentralItemToCart():
    data = await request.json
    response = await centralService.addCentralItemToCart(int(request.cart_id), data.get('branchProducts')) 
    return response

@app.route('/payPendingTransaction', methods=['PUT'])
@token_required
async def payPendingTransaction():
    data = await request.json
    response = await centralService.payPendingTransaction(data.get('transactionId'), data.get('amount')) 
    return response

""" SOCKET METHODS """

@app.websocket('/ws/criticalItems')
async def critical_items_ws():
    branch_id = websocket.args.get('branchId')
    await socketService.criticalItems(websocket, branch_id)

@app.websocket('/ws/dailyTransaction')
async def dailyTransaction():
    branch_id = websocket.args.get('branchId')
    await socketService.dailyTransaction(websocket, branch_id)

@app.websocket('/ws/dailyTransactionExacon')
async def dailyTransactionExacon():
    await socketService.dailyTransactionExacon(websocket)

@app.websocket('/ws/totalSales')
async def totalSales():
    branch_id = websocket.args.get('branchId')
    await socketService.totalSales(websocket, branch_id)

@app.websocket('/ws/totalCentralSales')
async def totalCentralSales():
    await socketService.totalCentralSales(websocket)

@app.websocket('/ws/dailyTransactionHQ')
async def dailyTransactionHQ():
    await socketService.dailyTransactionHQ(websocket)

@app.websocket('/ws/totalSalesHQ')
async def totalSalesHQ():
    await socketService.totalSalesHQ(websocket)

@app.websocket('/ws/criticalItemsHQ')
async def critical_items_ws_HQ():
    await socketService.criticalItemsHQ(websocket)

@app.websocket('/ws/criticalItemsBranches')
async def critical_items_ws_Branches():
    await socketService.criticalItemsBranches(websocket)

@app.websocket('/ws/criticalItemsWH')
async def critical_items_ws_WH():
    await socketService.criticalItemsWH(websocket)

@app.websocket('/ws/analyticsData')
async def analyticsData():
    branch_id = websocket.args.get('branchId')
    await socketService.analyticsData(websocket, branch_id)

@app.websocket('/ws/analysisReport')
async def analysisReport():
    branch_id = websocket.args.get('branchId')
    await socketService.analysisReport(websocket, branch_id)

@app.websocket('/ws/analyticsDataHQ')
async def analyticsDataHQ():
    fromDate = websocket.args.get('fromDate')
    toDate = websocket.args.get('toDate')
    branchId = websocket.args.get('branchId')
    await socketService.analyticsDataHQ(websocket,fromDate, toDate, branchId)

@app.websocket('/ws/analyticsGrossSalesDataHQ')
async def analyticsGrossSalesDataHQ():
    fromDate = websocket.args.get('fromDate')
    toDate = websocket.args.get('toDate')
    branchId = websocket.args.get('branchId')
    await socketService.analyticsGrossSalesDataHQ(websocket,fromDate, toDate, branchId)

@app.websocket('/ws/analysisReportHQ')
async def analysisReportHQ():
    await socketService.analysisReportHQ(websocket)

@app.route('/static/images/<filename>')
def get_image(filename):
    return send_from_directory(os.path.join(app.root_path, 'static/images'), filename)

if __name__ == '__main__':
    asyncio.run(init())
    uvicorn.run(app, host="0.0.0.0", port=5000)