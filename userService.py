import jwt
from config import SECRET_KEY  
from utils import create_response, hash_password_md5
from models import User, Branch, Department, Cart, Item, BranchItem
from tortoise import Tortoise
from decimal import Decimal

async def login_user(email, encryptedPassword):
    if not email or not encryptedPassword:
        return create_response(False, 'Please enter both username and password to proceed.'), 400

    user = await User.filter(email=email).first()
    if not user:
        return create_response(False, 'There was an issue with your login. Please try again.'), 200
    
    if user.isActive == False:
        return create_response(False, 'There was an issue with your login. Please try again.'), 200
    
    branch = await Branch.filter(id=user.branchId).first() if user.branchId else None
    if branch and not branch.isActive:
        return create_response(False, 'Your branch is inactive. Please contact support.'), 200
    
    if encryptedPassword == user.encryptedPassword:
        department = await Department.filter(id=user.departmentId).first() if user.departmentId else None
        cart = await Cart.filter(userId=user.id).first() if user.id else None
        user_details = {
            'name': user.name,
            'branchName': branch.name if branch else None,
            'branchId': branch.id if branch else None,
            'departmentId': department.id if department else None,
            'departmentName': department.name if department else None,
            'hasHeadAccess': user.hasHeadAccess,
            'cartId': cart.id if cart else None
        }

        payload = {
            "sub": str(user.id),
            "cartId": str(user_details["cartId"]) if user_details["cartId"] else None
        }

        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
        user_details["token"] = token
        return create_response(True, 'Logged In Successfully', user_details), 200

    return create_response(False, 'There was an issue with your login. Please try again.'), 200

async def getUsers(search = ""):
    sqlQuery = """
        SELECT u.*, d.name as deptName, b.name as branchName FROM users u 
        inner join departments d on d.Id = u.departmentId 
        left join branches b on b.id = u.branchId
        WHERE u.isActive = 1
    """
    params = []

    if search:
        sqlQuery += "WHERE u.name LIKE %s"
        params.append(f'%{search}%')

    sqlQuery += "ORDER BY u.name"

    connection = Tortoise.get_connection('default')
    result = await connection.execute_query(sqlQuery, tuple(params))

    items = result[1]

    itemList = [
        {
            "id": item['id'],
            "name": item['name'],
            "email": item['email'],
            "departmentId": item['departmentId'],
            "branchId": item['branchId'],
            "hasHeadAccess": bool(item['hasHeadAccess']),
            "deptName": item['deptName'],
            "branchName": item['branchName']
        }
        for item in items
    ]

    return create_response(True, "User list retrieved successfully.", itemList, None), 200

async def getUserById(userId):
    sqlQuery = """
        SELECT u.*, d.name as deptName, b.name as branchName 
        FROM users u 
        INNER JOIN departments d ON d.Id = u.departmentId 
        LEFT JOIN branches b ON b.id = u.branchId
        WHERE u.id = %s;
    """
    
    connection = Tortoise.get_connection('default')
    result = await connection.execute_query(sqlQuery, (userId,))
    if not result[1]:
        return create_response(False, "User not found.", None, None), 404

    item = result[1][0]

    user = {
        "id": item['id'],
        "name": item['name'],
        "email": item['email'],
        "departmentId": item['departmentId'],
        "branchId": item['branchId'],
        "hasHeadAccess": bool(item['hasHeadAccess']),
        "deptName": item['deptName'],
        "branchName": item['branchName'],
        "password": item['password']
    }

    return create_response(True, "User retrieved successfully.", user, None), 200

async def addUser(user):
    if '@gmail.com' not in user['email']:
        return create_response(False, "Invalid email. Only Gmail accounts are allowed."), 200

    hashed_password = hash_password_md5(user['password'])

    user = await User.create(
        name=user['name'],
        departmentId=user['departmentId'],
        branchId=user['branchId'],
        hasHeadAccess = user['hasHeadAccess'] if user['hasHeadAccess'] is not None else False,
        encryptedPassword=hashed_password,
        email=user['email'],
        password = user['password'],
        isActive = True
    )
    if int(user.departmentId) == 1 or int(user.departmentId) == 4: 
        await Cart.create(userId=user.id, subTotal=0.00)
        
    return create_response(True, "User added successfully.", user.id), 201

async def editUser(user):
    existing_user = await User.get(id=user['id'])
    if '@gmail.com' not in user['email']:
        return create_response(False, "Invalid email. Only Gmail accounts are allowed."), 400
    
    if not existing_user:
        return create_response(False, "User not found."), 404
    
    if 'name' in user and user['name'] is not None:
        existing_user.name = user['name']
    if 'departmentId' in user and user['departmentId'] is not None:
        existing_user.departmentId = user['departmentId']
    if 'branchId' in user and user['branchId'] is not None:
        existing_user.branchId = user['branchId']
    if 'hasHeadAccess' in user and user['hasHeadAccess'] is not None:
        existing_user.hasHeadAccess = user['hasHeadAccess']
    if 'email' in user and user['email'] is not None:
        existing_user.email = user['email']
    if 'password' in user and user['password'] is not None:
        existing_user.password = user['password']
        existing_user.encryptedPassword = hash_password_md5(user['password'])

    await existing_user.save()

    return create_response(True, "User updated successfully.", existing_user.id, None), 200

async def getDepartments():
    departments = await Department.all().order_by("name")
    return [{"id": d.id, "name": d.name} for d in departments]

async def getBranches():
    branches = await Branch.filter(isActive=True).order_by("name")
    return [{"id": b.id, "name": b.name} for b in branches]

async def setInactiveUser(id):
    existing_user = await User.get(id=id)
    
    if not existing_user:
        return create_response(False, "User not found."), 404
    
    existing_user.isActive = False

    await existing_user.save()

    return create_response(True, "User updated successfully.", existing_user.id, None), 200

async def setBranchInactive(branchId):
    branch = await Branch.get_or_none(id=branchId)
    if branch:
        branch.isActive = False
        await branch.save()
        return create_response(True, "Branch deleted successfully.", None, None), 200
    return create_response(False, "An error occured unable to delete branch.", None, None), 200

async def saveBranch(branchId, name):
    if branchId == 0:
        branch = await Branch.create(name=name, isActive=True)
        
        active_items = await Item.filter(isManaged=1)

        branch_items = [
            BranchItem(itemId=item.id, branchId=branch.id, quantity=Decimal(0.00)) 
            for item in active_items
        ]

        await BranchItem.bulk_create(branch_items)

        return create_response(True, "Branch saved successfully.", None, None), 200    
    else:
        branch = await Branch.get_or_none(id=branchId)
        if branch:
            branch.name = name
            await branch.save()
            return create_response(True, "Branch updated successfully.", None, None), 200
        return create_response(False, "An error occurred, unable to update branch.", None, None), 200


