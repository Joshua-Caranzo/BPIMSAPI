from models import Customer, Branch, Transaction, Cart
from utils import create_response, sanitize_filename
from config import CUSTOMER_IMAGES, BASE_URL
import os
from tortoise.queryset import Q 

async def getCustomerList(branchId = None, search = ""):

    customer_query = Customer.all().order_by('name')

    if branchId:
        customer_query = customer_query.filter(branchId=branchId)

    if search:
        customer_query = customer_query.filter(Q(name__icontains=search))

    customers = await customer_query.values("id", "name", "branchId")

    return create_response(True, "Customer list retrieved successfully.", customers, None), 200

async def getCustomer(id):
    if id:
        base_url = BASE_URL
        customer = await Customer.get_or_none(id=id)
        
        if customer:
            branch = await Branch.get_or_none(id=customer.branchId)
            
            transactions = await Transaction.filter(customerId=id).all()

            orderHistory = [
                {
                    "id": transaction.id,
                    "totalAmount": transaction.totalAmount,
                    "amountReceived": transaction.amountReceived,
                    "slipNo": transaction.slipNo,
                    "transactionDate": transaction.transactionDate,
                }
                for transaction in transactions
            ]

            customer_data = {
                'id': customer.id,
                'name': customer.name,
                'contactNumber1': customer.contactNumber1,
                'contactNumber2': customer.contactNumber2,
                'totalOrderAmount': customer.totalOrderAmount,
                'branchId': customer.branchId,
                'branch': branch.name if branch else None,
                'fileName': customer.fileName,
                "fileUrl": f"{base_url}/getCustomerImage?fileName={customer.fileName}" if customer.fileName else None,
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
            name = name
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
            user_images_dir = CUSTOMER_IMAGES
            if not os.path.exists(user_images_dir):
                os.makedirs(user_images_dir)
            
            file_extension = os.path.splitext(file.filename)[1]
            sanitized_name = sanitize_filename(name)
            new_file_name = f"{sanitized_name}_{customerId}{file_extension}"
            file_path = os.path.join(user_images_dir, new_file_name)
            
            with open(file_path, 'wb') as f:
                f.write(file.read())

            existing_customer = await Customer.get_or_none(id=customerId)
            existing_customer.fileName = new_file_name
            await existing_customer.save()

    return create_response(True, message, customerId, None), 200

async def deleteCustomer(id):
    customer = await Customer.get_or_none(id=id)
    
    if not customer:
        return create_response(False, "Customer not found.", None, None), 200

    if customer.fileName:
        image_path = os.path.join(CUSTOMER_IMAGES, customer.fileName)
        if os.path.exists(image_path):
            os.remove(image_path)
            
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


