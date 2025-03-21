from reportlab.pdfgen import canvas
from io import BytesIO
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from models import Item, Transaction, TransactionItem, Branch, Customer, User
from decimal import Decimal
from reportlab.platypus import Image
from datetime import datetime

async def generate_receipt_pdf(transaction, transaction_items):
    buffer = BytesIO()
    logo_path = "static/images/appstore.png"  # Local path to the logo image

    # Define PDF dimensions (80mm width, 180mm height, converted to points)
    width = 80 * 2.83  # 80mm to points
    base_height = 50  # Base height for headers, footers, and extra space
    margin = 10
    right_margin = width - margin
    line_height = 12
    calculated_height = base_height + (len(transaction_items) * line_height * 2.5)  # Dynamic height
    height = max(calculated_height, 180 * 2.83)

    y = 410  # Start from the top of the page
    c = canvas.Canvas(buffer, pagesize=(width, height))

    # Register a custom font (DejaVu Sans)
    pdfmetrics.registerFont(TTFont('DejaVu', 'DejaVuSans.ttf'))

    # Add logo (centered)
    logo_width = 80
    logo_height = 80
    c.drawImage(logo_path, (width - logo_width) / 2, y, width=logo_width, height=logo_height, mask='auto')
    y -= line_height + 10  # Move down after the logo

    # Business name (centered)
    c.setFont("DejaVu", 12)
    business_name = "Balay Panday Hardware"
    business_name_width = c.stringWidth(business_name, "DejaVu", 12)
    c.drawString((width - business_name_width) / 2, y, business_name)
    y -= line_height * 2

    # Customer name (if available)
    c.setFont("DejaVu", 10)
    if transaction['customerName']:
        c.drawString(margin, y, f"Customer: {transaction['customerName']}")
        y -= line_height * 1.5


    # Transaction date
    transaction_date = transaction['transactionDate']  # This is already a datetime object
    formatted_date = transaction_date.strftime('%B %d, %Y %I:%M %p')
    c.drawString(margin, y, f"Date: {formatted_date}")
    y -= line_height * 1.5

    # Cashier
    c.drawString(margin, y, f"Cashier: {transaction['cashier']}")
    y -= line_height * 1.5

    # Mode of payment
    c.drawString(margin, y, "Mode of Payment: Cash")
    y -= line_height * 1.5

    # Number of items
    c.drawString(margin, y, f"Number of Items: {len(transaction_items)}")
    y -= line_height * 1.5

    c.drawString(margin, y, f"Slip Number: {transaction['slipNo']}")
    y -= line_height * 1.5

    # Branch
    c.drawString(margin, y, f"Branch: {transaction['branch']}")
    y -= line_height * 2

    # Line separator
    c.setDash(2, 2)  # Creates a dashed line with 2 units on, 2 units off
    c.line(margin, y, right_margin, y)
    c.setDash()  # Reset to solid lines for future drawings
    y -= 20

    # Store pick-up
    c.drawString(margin, y, "Store Pick-Up")
    y -= line_height

    # Line separator
    c.setDash(2, 2)  # Creates a dashed line with 2 units on, 2 units off
    c.line(margin, y, right_margin, y)
    c.setDash()  # Reset to solid lines for future drawings
    y -= 20

    # List of items
    c.setFont("DejaVu", 9)
    for item in transaction_items:
        item_name = item['name']
        if len(item_name) > 20:  # Truncate long item names
            item_name = item_name[:20] + '...'
        item_quantity = item['quantity']
        item_price = float(item['price'])
        item_amount = float(item['amount'])

        c.drawString(margin, y, item_name)
        y -= line_height

        if item['sellByUnit']:
            quantity_display = f"{int(item_quantity)}"  
        else:
            quantity_display = f"{item_quantity:.2f}" 

        quantity_price_line = f"     {quantity_display} X ₱ {item_price:.2f}"  
        c.drawString(margin, y, quantity_price_line)

        total_amount_text = f"₱ {item_amount:.2f}"
        total_amount_width = c.stringWidth(total_amount_text, "DejaVu", 9)
        c.drawString(right_margin - total_amount_width, y, total_amount_text)
        
        y -= line_height * 1.2 

    c.setDash(2, 2) 
    c.line(margin, y, right_margin, y)
    c.setDash() 
    y -= 20

    c.setFont("DejaVu", 10)

    # Subtotal
    subTotal_label = "Sub Total:"
    c.drawString(margin, y, subTotal_label)

    subTotal_text = f"₱ {float(transaction['subTotal']):.2f}"
    subTotal_width = c.stringWidth(subTotal_text, "DejaVu", 10)
    c.drawString(right_margin - subTotal_width, y, subTotal_text)
    y -= line_height * 1.5

    # Delivery fee (if applicable)
    if transaction['deliveryFee']:
        delivery_label = "Delivery Fee:"
        c.drawString(margin, y, delivery_label)

        delivery_text = f"₱ {float(transaction['deliveryFee']):.2f}"
        delivery_width = c.stringWidth(delivery_text, "DejaVu", 10)
        c.drawString(right_margin - delivery_width, y, delivery_text)
        y -= line_height * 1.5

    # Discount (if applicable)
    if transaction['discount']:
        discount_label = "Discount:"
        c.drawString(margin, y, discount_label)

        discount_text = f"₱ {float(transaction['discount']):.2f}"
        discount_width = c.stringWidth(discount_text, "DejaVu", 10)
        c.drawString(right_margin - discount_width, y, discount_text)
        y -= line_height * 1.5

    # Total amount (Bold)
    c.setFont("DejaVu", 10)
    total_label = "TOTAL:"
    c.drawString(margin, y, total_label)

    total_text = f"₱ {float(transaction['totalAmount']):.2f}"
    total_width = c.stringWidth(total_text, "DejaVu", 10)
    c.drawString(right_margin - total_width, y, total_text)
    y -= line_height * 1.5
    c.setFont("DejaVu", 10)  # Reset font

    # Cash received
    cash_label = "Cash:"
    c.drawString(margin, y, cash_label)

    cash_text = f"₱ {float(transaction['amountReceived']):.2f}"
    cash_width = c.stringWidth(cash_text, "DejaVu", 10)
    c.drawString(right_margin - cash_width, y, cash_text)
    y -= line_height * 1.5

    # Change
    change = float(transaction['amountReceived']) - float(transaction['totalAmount'])
    change_label = "Change:"
    c.drawString(margin, y, change_label)

    change_text = f"₱ {change:.2f}"
    change_width = c.stringWidth(change_text, "DejaVu", 10)
    c.drawString(right_margin - change_width, y, change_text)
    y -= line_height * 1.5


    # Line separator
    c.setDash(2, 2)  # Creates a dashed line with 2 units on, 2 units off
    c.line(margin, y, right_margin, y)
    c.setDash()  # Reset to solid lines for future drawings
    y -= 10

    # Footer text (centered)
    c.setFont("DejaVu", 8)
    footer_text = "Thank you for building with us!"
    footer_text_width = c.stringWidth(footer_text, "DejaVu", 8)
    c.drawString((width - footer_text_width) / 2, y, footer_text)
    y -= line_height

    # Footer note (centered)
    footer_note = "Please keep this slip for your records."
    footer_note_width = c.stringWidth(footer_note, "DejaVu", 8)
    c.drawString((width - footer_note_width) / 2, y, footer_note)
    y -= line_height

    # Official receipt note (centered)
    official_receipt_note = "For official receipts, please visit the Receipt Counter."
    official_receipt_note_width = c.stringWidth(official_receipt_note, "DejaVu", 8)
    c.drawString((width - official_receipt_note_width) / 2, y, official_receipt_note)

    # Save the PDF
    c.showPage()
    c.save()

    buffer.seek(0)
    return buffer

async def generateReceipt(transactionId):
    transaction = await Transaction.get_or_none(id=transactionId)
    
    if not transaction:
        return None
    
    branch = await Branch.get_or_none(id=transaction.branchId)
    customer = await Customer.get_or_none(id=transaction.customerId) if transaction.customerId else None
    transactionItems = await TransactionItem.filter(transactionId=transactionId)
    user = await User.get_or_none(id = transaction.cashierId)
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
    sub_total = (transaction.totalAmount or Decimal(0)) - (transaction.deliveryFee or Decimal(0)) + (transaction.discount or Decimal(0))

    transactionData = {
        "transaction": {
            "id": transaction.id,
            "totalAmount": transaction.totalAmount,
            "amountReceived": transaction.amountReceived,
            "slipNo": transaction.slipNo,
            "transactionDate": transaction.transactionDate,
            "branch": branch.name if branch else None,
            "deliveryFee": transaction.deliveryFee,
            "discount": transaction.discount,
            "customerName": customer.name if customer else None,
            "cashier": user.name,
            "subTotal": sub_total
        },
        "transactionItems": items
    }
    
    buffer = await generate_receipt_pdf(transactionData['transaction'], transactionData['transactionItems'])
    return buffer