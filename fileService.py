from reportlab.pdfgen import canvas
from io import BytesIO
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from models import Item, Transaction, TransactionItem, Branch, Customer
from decimal import Decimal

async def generate_receipt_pdf(transaction, transaction_items):
    buffer = BytesIO()

    width = 80 * 2.83
    height = 180 * 2.83
    c = canvas.Canvas(buffer, pagesize=(width, height))

    pdfmetrics.registerFont(TTFont('DejaVu', 'DejaVuSans.ttf'))

    margin = 10
    right_margin = width - margin
    line_height = 12
    y = height - 20 

    c.setFont("DejaVu", 14)
    business_name = "BALAY PANDAY HARDWARE"
    business_name_width = c.stringWidth(business_name, "DejaVu", 14)
    c.drawString((width - business_name_width) / 2, y, business_name)
    y -= line_height * 1.5

    c.setFont("DejaVu", 10)
    contact_info = "Phone: (123) 456-7890"
    contact_info_width = c.stringWidth(contact_info, "DejaVu", 10)
    c.drawString((width - contact_info_width) / 2, y, contact_info)
    y -= line_height * 2

    c.setFont("DejaVu", 12)
    slip_no = f"SLIP# {transaction['slipNo']}"
    slip_no_width = c.stringWidth(slip_no, "DejaVu", 12)
    c.drawString((width - slip_no_width) / 2, y, slip_no)
    y -= line_height * 1.5

    c.setFont("DejaVu", 10)
    if transaction['customerName']:
        c.drawString(margin, y, f"Customer: {transaction['customerName']}")
        y -= line_height

    transaction_date = transaction['transactionDate']  # This is already a datetime object
    formatted_date = transaction_date.strftime('%B %d, %Y %I:%M %p') 
    formatted_date = transaction_date.strftime('%B %d, %Y %I:%M %p')
    c.drawString(margin, y, f"Date: {formatted_date}")
    y -= line_height * 2

    c.setFont("DejaVu", 10)
    c.drawString(margin, y, "ITEMS:")
    y -= line_height

    c.line(margin, y, right_margin, y)
    y -= 10

    c.setFont("DejaVu", 9)
    for item in transaction_items:
        item_name = item['name']
        if len(item_name) > 20: 
            item_name = item_name[:20] + '...'

        item_line = f"{item['quantity']}x {item_name}"
        c.drawString(margin, y, item_line)

        price_line = f"₱ {float(item['price']):.2f} each"
        price_line_width = c.stringWidth(price_line, "DejaVu", 9)
        c.drawString(right_margin - price_line_width, y, price_line)
        y -= line_height

        total_amount = f"₱ {float(item['amount']):.2f}"
        total_amount_width = c.stringWidth(total_amount, "DejaVu", 9)
        c.drawString(right_margin - total_amount_width, y, total_amount)
        y -= line_height

    c.line(margin, y, right_margin, y)
    y -= 10

    c.setFont("DejaVu", 10)
    c.drawString(margin, y, f"Sub Total: ₱ {float(transaction['subTotal'])}")
    y -= line_height

    if transaction['deliveryFee']:
        c.drawString(margin, y, f"Delivery Fee: ₱ {float(transaction['deliveryFee'])}")
        y -= line_height

    if transaction['discount']:
        c.drawString(margin, y, f"Discount: ₱ {float(transaction['discount'])}")
        y -= line_height

    c.drawString(margin, y, f"TOTAL: ₱ {float(transaction['totalAmount'])}")
    y -= line_height

    c.drawString(margin, y, f"Cash: ₱ {float(transaction['amountReceived'])}")
    y -= line_height

    change = float(transaction['amountReceived']) - float(transaction['totalAmount'])
    c.drawString(margin, y, f"Change: ₱ {change:.2f}")
    y -= line_height * 2

    c.line(margin, y, right_margin, y)
    y -= 10

    c.setFont("DejaVu", 8)
    footer_text = "Thank you for building with us!"
    footer_text_width = c.stringWidth(footer_text, "DejaVu", 8)
    c.drawString((width - footer_text_width) / 2, y, footer_text)
    y -= line_height

    c.setFont("DejaVu", 8)
    footer_text = "Please keep this slip for your records."
    footer_text_width = c.stringWidth(footer_text, "DejaVu", 8)
    c.drawString((width - footer_text_width) / 2, y, footer_text)
    y -= line_height

    c.setFont("DejaVu", 8)
    footer_note = "For official receipts, please visit the Receipt Counter."
    footer_note_width = c.stringWidth(footer_note, "DejaVu", 8)
    c.drawString((width - footer_note_width) / 2, y, footer_note)

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
                "amount": tItem.amount
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
            "subTotal": sub_total
        },
        "transactionItems": items
    }
    
    buffer = await generate_receipt_pdf(transactionData['transaction'], transactionData['transactionItems'])
    return buffer