from tortoise.models import Model
from tortoise import fields

class User(Model):
    id = fields.IntField(pk=True)
    email = fields.CharField(max_length=255, null=False)
    name = fields.CharField(max_length=255, null=False)
    encryptedPassword = fields.CharField(max_length=500, null=False)
    password = fields.CharField(max_length=255, null=False)
    departmentId = fields.IntField(null = False)
    branchId = fields.IntField(null = True)
    hasHeadAccess = fields.BooleanField(null=False, default=False)
    isActive = fields.BooleanField(null=False, default=True)

    class Meta:
        table = "users"
        
class Branch(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255, null=False)
    isActive = fields.BooleanField(null=False, default=True)
    class Meta:
        table = "branches"

class Department(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255, null=False)

    class Meta:
        table = "departments"
        
class Item(Model):
    id = fields.IntField(pk=True)
    categoryId = fields.IntField(null=True)
    name = fields.CharField(max_length=255, null=False)
    price = fields.DecimalField(max_digits=10, decimal_places=2, null=False)
    cost = fields.DecimalField(max_digits=10, decimal_places=2, null=False)
    isManaged = fields.BooleanField(null=False, default=True)
    imagePath = fields.CharField(max_length=255, null=True)
    storeCriticalValue = fields.DecimalField(max_digits=10, decimal_places=2, null=False)
    sellByUnit = fields.BooleanField(null = False)
    whCriticalValue = fields.DecimalField(max_digits=10, decimal_places=2, null=False)
    unitOfMeasure = fields.CharField(max_length=20, null=True)
    imageId = fields.CharField(max_length=255, null=True)

    class Meta:
        table = "items"

class Category(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255, null=False)

    class Meta:
        table = "categories"

class Cart(Model):
    id = fields.IntField(null=False, pk=True)
    userId = fields.IntField(null=False)
    discount = fields.DecimalField(max_digits=18, decimal_places=2, null=True)
    deliveryFee = fields.DecimalField(max_digits=18, decimal_places=2, null=True)
    subTotal = fields.DecimalField(max_digits=18, decimal_places=2, null=False)
    customerId = fields.CharField(max_length=500, null=True)

    class Meta:
        table = "carts"

class CartItems(Model):
    id = fields.IntField(null=False, pk=True)
    cartId = fields.IntField(null=False)
    branchItemId = fields.IntField(null=False)
    quantity = fields.DecimalField(max_digits=10, decimal_places=2, null=False)

    class Meta:
        table = "cartitems"

class Transaction(Model):
    id = fields.IntField(pk=True)
    amountReceived = fields.DecimalField(max_digits=18, decimal_places=2, null=False)
    totalAmount = fields.DecimalField(max_digits=18, decimal_places=2, null=False)
    cashierId = fields.IntField(null=False)
    slipNo = fields.CharField(max_length=255, null=False)
    transactionDate = fields.DatetimeField(null=False)
    customerId = fields.CharField(max_length=500, null=True)
    branchId = fields.IntField(null=False)
    profit = fields.DecimalField(max_digits=18, decimal_places=2, null=False)
    deliveryFee = fields.DecimalField(max_digits=10, decimal_places=2, null = True)
    discount = fields.DecimalField(max_digits=10, decimal_places=2, null = True)
    isVoided = fields.BooleanField(null=False, default=False)
    isPaid = fields.BooleanField(null=False, default=True)
    isExacon = fields.BooleanField(null=False, default=False)

    class Meta:
        table = "transactions"

class TransactionItem(Model):
    id = fields.IntField(pk=True)
    transactionId = fields.IntField(null=False)
    itemId = fields.IntField(null=False)
    quantity = fields.DecimalField(max_digits=10, decimal_places=2, null=False)
    amount = fields.DecimalField(max_digits=10, decimal_places=2, null=False)

    class Meta:
        table = "transactionitems"

class Customer(Model):
    id = fields.IntField(pk=True)
    name =  fields.CharField(max_length=255, null=False)
    branchId = fields.IntField(null=True)
    contactNumber1 = fields.CharField(max_length=20, null=True)
    contactNumber2 = fields.CharField(max_length=20, null=True)
    totalOrderAmount = fields.DecimalField(max_digits=18, decimal_places=2, null=False)
    fileName = fields.CharField(max_length=255, null=True)
    imageId = fields.CharField(max_length=255, null=True)
    isLoyalty = fields.BooleanField(null=True)

    class Meta:
        table = "customers"

class BranchItem(Model):
    id= fields.IntField(null=False, pk=True)
    branchId = fields.IntField(null=False)
    itemId = fields.IntField(null=False)
    quantity = fields.DecimalField(max_digits=10, decimal_places=2, null=False)

    class Meta:
        table = "branchitem"
        unique_together = ("branchId", "itemId")

class StockInput(Model):
    id = fields.IntField(null=False, pk=True)
    qty = fields.DecimalField(max_digits=10, decimal_places=2, null=False)
    deliveryDate = fields.DateField(null=False)
    deliveredBy = fields.CharField(max_length=255, null=False)
    expectedQty = fields.DecimalField(max_digits=10, decimal_places=2, null=False)
    actualQty = fields.DecimalField(max_digits=10, decimal_places=2, null=False)
    branchItemId = fields.IntField(null=False)

    class Meta:
        table = "stockinputs"

class WareHouseItem(Model):
    id = fields.IntField(null=False, pk=True)
    itemId = fields.IntField(null=False)
    quantity = fields.DecimalField(max_digits=10, decimal_places=2, null=False)

    class Meta:
        table = "warehouseitems"

class WHStockInput(Model):
    id = fields.IntField(null=False, pk=True)
    qty = fields.DecimalField(max_digits=10, decimal_places=2, null=False)
    deliveryDate = fields.DateField(null=False)
    deliveredBy = fields.IntField(null=True)
    expectedQty = fields.DecimalField(max_digits=10, decimal_places=2, null=False)
    actualQty = fields.DecimalField(max_digits=10, decimal_places=2, null=False)
    itemId = fields.IntField(null=False)
    class Meta:
        table = "whstockinputs"

class Supplier(Model):
    id = fields.IntField(null=False, pk=True)
    name =  fields.CharField(max_length=255, null=False)
    contactNumber1 = fields.CharField(max_length=50, null=True)
    contactNumber2 = fields.CharField(max_length=50, null=True)
    address = fields.CharField(max_length=1000, null=True)

    class Meta:
        table = "suppliers"

class BranchTransferHistory(Model):
    id= fields.IntField(null=False, pk=True)
    branchFromId = fields.IntField(null=False)
    branchToId = fields.IntField(null=False)
    quantity = fields.DecimalField(max_digits=10, decimal_places=2, null=False)
    date = fields.DatetimeField(null=False)

    class Meta:
        table = "branchtransferhistory"

class SupplierReturn(Model):
    id = fields.IntField(pk=True)
    supplierId = fields.IntField(null=False)
    whItemId = fields.IntField(null=False)
    reason = fields.CharField(max_length=5000, null=False)
    quantity = fields.DecimalField(max_digits=10, decimal_places=2, null=False)
    date = fields.DatetimeField(null=False)

    class Meta:
        table = "supplierreturn"

class BranchReturn(Model):
    id = fields.IntField(pk=True)
    branchItemId = fields.IntField(null=False)
    reason = fields.CharField(max_length=5000, null=False)
    quantity = fields.DecimalField(max_digits=10, decimal_places=2, null=False)
    date = fields.DatetimeField(null=False)

    class Meta:
        table = "branchreturn"

class LoyaltyCard(Model):
    id = fields.IntField(pk=True)
    validYear =  fields.CharField(max_length = 50, null=False)
    isValid = fields.BooleanField(null=False, default=False)

    class Meta:
        table = "loyaltycards"

class ItemReward(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255, null=False)

    class Meta:
        table = "itemrewards"

class LoyaltyStages(Model):
    id = fields.IntField(pk=True)
    orderId = fields.IntField(null=False)
    loyaltyCardId = fields.IntField(null=False)
    itemRewardId = fields.IntField(null=True)
    
    class Meta:
        table = "loyaltyStages"

class LoyaltyCustomer(Model):
    id = fields.IntField(pk=True)
    stageId = fields.IntField(null=False)
    customerId = fields.IntField(null=False)
    isDone = fields.BooleanField(null=False, default=False)
    dateDone =  fields.DateField(null=True)
    itemId = fields.IntField(null=True)
    
    class Meta:
        table = "loyaltycustomers"