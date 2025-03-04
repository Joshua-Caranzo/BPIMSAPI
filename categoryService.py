from models import Category
from utils import create_response

async def get_categories():
    categories = await Category.filter(id__in=[11, 1, 8, 13]).order_by('name')

    category_list = [
        {"id": 0, "name": "All"}, 
        {"id": -1, "name": "Hot Items"},  
    ]

    category_list.extend([
        {"id": category.id, "name": category.name}
        for category in categories
    ])

    return create_response(True, 'Categories Successfully Retrieved', category_list), 200

async def getCategoriesHQ():
    categories = await Category.filter(id__in=[11, 1, 8, 13]).order_by('name')

    category_list = [
        {"id": 0, "name": "All"}
    ]
    category_list.extend([
        {"id": category.id, "name": category.name}
        for category in categories
    ])
    
    return create_response(True, 'Categories Successfully Retrieved', category_list), 200


