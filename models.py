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

    class Meta:
        table = "users"
        
class Branch(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255, null=False)

    class Meta:
        table = "branches"

class Department(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255, null=False)

    class Meta:
        table = "departments"
        
class Item(Model):
    id = fields.IntField(pk=True)
    categoryId = fields.IntField(null=False)
    name = fields.CharField(max_length=255, null=False)
    price = fields.DecimalField(max_digits=10, decimal_places=2, null=False)
    cost = fields.DecimalField(max_digits=10, decimal_places=2, null=False)
    isManaged = fields.BooleanField(null=False, default=True)
    imagePath = fields.CharField(max_length=255, null=True)
    criticalValue = fields.DecimalField(max_digits=10, decimal_places=2, null=False)
    sellByUnit = fields.BooleanField(null = False)
    moq = fields.DecimalField(max_digits=10, decimal_places=2, null=False)
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
    itemId = fields.IntField(null=False)
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
    moq = fields.DecimalField(max_digits=10, decimal_places=2, null=False)
    deliveryDate = fields.DateField(null=False)
    deliveredBy = fields.CharField(max_length=255, null=False)
    expectedQty = fields.DecimalField(max_digits=10, decimal_places=2, null=False)
    actualQty = fields.DecimalField(max_digits=10, decimal_places=2, null=False)
    itemId = fields.IntField(null=False)
    class Meta:
        table = "whstockinputs"