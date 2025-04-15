from reportlab.pdfgen import canvas
from io import BytesIO
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from models import Item, Transaction, TransactionItem, Branch, Customer, User
from decimal import Decimal
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime, timedelta, timezone
from tortoise import Tortoise

async def generate_receipt_pdf(transaction, transaction_items):
    buffer = BytesIO()
    logo_path = "static/images/appstore.png"  

    width = 80 * 2.83  
    base_height = 50 
    margin = 10
    right_margin = width - margin
    line_height = 12
    calculated_height = base_height + (len(transaction_items) * line_height * 2.5)  
    height = max(calculated_height, 180 * 2.83)

    y = 410  
    c = canvas.Canvas(buffer, pagesize=(width, height))

    pdfmetrics.registerFont(TTFont('DejaVu', 'DejaVuSans.ttf'))

    logo_width = 80
    logo_height = 80
    c.drawImage(logo_path, (width - logo_width) / 2, y, width=logo_width, height=logo_height, mask='auto')
    y -= line_height + 10  

    c.setFont("DejaVu", 12)
    business_name = "Balay Panday Hardware"
    business_name_width = c.stringWidth(business_name, "DejaVu", 12)
    c.drawString((width - business_name_width) / 2, y, business_name)
    y -= line_height * 2

    c.setFont("DejaVu", 10)
    if transaction['customerName']:
        c.drawString(margin, y, f"Customer: {transaction['customerName']}")
        y -= line_height * 1.5

    transaction_date = transaction['transactionDate'] 
    formatted_date = transaction_date.strftime('%B %d, %Y %I:%M %p')
    c.drawString(margin, y, f"Date: {formatted_date}")
    y -= line_height * 1.5

    c.drawString(margin, y, f"Cashier: {transaction['cashier']}")
    y -= line_height * 1.5

    c.drawString(margin, y, "Mode of Payment: Cash")
    y -= line_height * 1.5

    c.drawString(margin, y, f"Number of Items: {len(transaction_items)}")
    y -= line_height * 1.5

    c.drawString(margin, y, f"Slip Number: {transaction['slipNo']}")
    y -= line_height * 1.5

    c.drawString(margin, y, f"Branch: {transaction['branch']}")
    y -= line_height * 2

    c.setDash(2, 2) 
    c.line(margin, y, right_margin, y)
    c.setDash()  
    y -= 20

    c.drawString(margin, y, "Store Pick-Up")
    y -= line_height

    c.setDash(2, 2)  
    c.line(margin, y, right_margin, y)
    c.setDash()  
    y -= 20

    c.setFont("DejaVu", 9)
    for item in transaction_items:
        item_name = item['name']
        if len(item_name) > 20: 
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

    subTotal_label = "Sub Total:"
    c.drawString(margin, y, subTotal_label)

    subTotal_text = f"₱ {float(transaction['subTotal']):.2f}"
    subTotal_width = c.stringWidth(subTotal_text, "DejaVu", 10)
    c.drawString(right_margin - subTotal_width, y, subTotal_text)
    y -= line_height * 1.5

    if transaction['deliveryFee']:
        delivery_label = "Delivery Fee:"
        c.drawString(margin, y, delivery_label)

        delivery_text = f"₱ {float(transaction['deliveryFee']):.2f}"
        delivery_width = c.stringWidth(delivery_text, "DejaVu", 10)
        c.drawString(right_margin - delivery_width, y, delivery_text)
        y -= line_height * 1.5

    if transaction['discount']:
        discount_label = "Discount:"
        c.drawString(margin, y, discount_label)

        discount_text = f"₱ {float(transaction['discount']):.2f}"
        discount_width = c.stringWidth(discount_text, "DejaVu", 10)
        c.drawString(right_margin - discount_width, y, discount_text)
        y -= line_height * 1.5

    c.setFont("DejaVu", 10)
    total_label = "TOTAL:"
    c.drawString(margin, y, total_label)

    total_text = f"₱ {float(transaction['totalAmount']):.2f}"
    total_width = c.stringWidth(total_text, "DejaVu", 10)
    c.drawString(right_margin - total_width, y, total_text)
    y -= line_height * 1.5
    c.setFont("DejaVu", 10) 

    cash_label = "Cash:"
    c.drawString(margin, y, cash_label)

    cash_text = f"₱ {float(transaction['amountReceived']):.2f}"
    cash_width = c.stringWidth(cash_text, "DejaVu", 10)
    c.drawString(right_margin - cash_width, y, cash_text)
    y -= line_height * 1.5

    change = float(transaction['amountReceived']) - float(transaction['totalAmount'])
    change_label = "Change:"
    c.drawString(margin, y, change_label)

    change_text = f"₱ {change:.2f}"
    change_width = c.stringWidth(change_text, "DejaVu", 10)
    c.drawString(right_margin - change_width, y, change_text)
    y -= line_height * 1.5


    c.setDash(2, 2) 
    c.line(margin, y, right_margin, y)
    c.setDash()  
    y -= 10

    c.setFont("DejaVu", 8)
    footer_text = "Thank you for building with us!"
    footer_text_width = c.stringWidth(footer_text, "DejaVu", 8)
    c.drawString((width - footer_text_width) / 2, y, footer_text)
    y -= line_height

    footer_note = "Please keep this slip for your records."
    footer_note_width = c.stringWidth(footer_note, "DejaVu", 8)
    c.drawString((width - footer_note_width) / 2, y, footer_note)
    y -= line_height

    official_receipt_note = "For official receipts, please visit the Receipt Counter."
    official_receipt_note_width = c.stringWidth(official_receipt_note, "DejaVu", 8)
    c.drawString((width - official_receipt_note_width) / 2, y, official_receipt_note)

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
    return 

async def generateSalesReport(from_date_str, to_date_str, branch_id):
    branchName = ""
    if(branch_id != '0'):
        branch = await Branch.get_or_none(id=branch_id)
    if branch:
        branchName = branch.name
    buffer = await generate_sales_report_pdf(from_date_str, to_date_str, branch_id, branchName)
    return buffer

async def generate_sales_report_pdf(from_date_str, to_date_str, branch_id, branch_name="All Branches"):
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(letter),
                            rightMargin=0.5*inch, leftMargin=0.5*inch,
                            topMargin=0.5*inch, bottomMargin=0.5*inch)
        
        pdfmetrics.registerFont(TTFont('DejaVu', 'DejaVuSans.ttf'))
        
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER))
        styles.add(ParagraphStyle(name='Header', fontSize=12, textColor=colors.white))
        styles.add(ParagraphStyle(name='OrangeText', textColor=colors.HexColor('#fe6500')))
        
        now_sg = datetime.now(timezone.utc) + timedelta(hours=8)
        connection = Tortoise.get_connection('default')
        
        branch_filter = f"AND tr.branchId = {branch_id}" if branch_id != 0 else ""
        summary_query = f"""
            SELECT 
                COALESCE(SUM(tr.totalAmount), 0) AS gross_sales,
                COALESCE(SUM(tr.discount), 0) AS total_discount,
                COALESCE(SUM(tr.totalAmount), 0) - COALESCE(SUM(tr.discount), 0) AS net_sales,
                COALESCE(SUM(costs.item_cost), 0) AS item_cost,
                (COALESCE(SUM(tr.totalAmount), 0) - COALESCE(SUM(tr.discount), 0)) - COALESCE(SUM(costs.item_cost), 0) AS gross_profit
            FROM transactions tr
            LEFT JOIN (
                SELECT 
                    ti.transactionId,
                    SUM(ti.quantity * i.cost) AS item_cost
                FROM transactionitems ti
                JOIN items i ON ti.itemId = i.id
                GROUP BY ti.transactionId
            ) AS costs ON tr.id = costs.transactionId
            WHERE DATE(tr.transactionDate) BETWEEN '{from_date_str}' AND '{to_date_str}'
            AND tr.isVoided = 0
            AND tr.isPaid = 1
            {branch_filter}
        """
        summary_result = await connection.execute_query_dict(summary_query)
        summary = summary_result[0] if summary_result else {}
        
        if from_date_str == to_date_str:
            time_query = f"""
                SELECT 
                    HOUR(tr.transactionDate) AS hour,
                    COALESCE(SUM(tr.totalAmount), 0) AS totalAmount
                FROM transactions tr
                WHERE DATE(tr.transactionDate) = '{from_date_str}'
                AND HOUR(tr.transactionDate) BETWEEN 7 AND 17
                AND tr.isVoided = 0 AND tr.isPaid = 1
                {branch_filter}
                GROUP BY HOUR(tr.transactionDate)
                ORDER BY hour
            """
            time_data = await connection.execute_query_dict(time_query)
        else:
            time_query = f"""
                SELECT 
                    DATE(tr.transactionDate) AS date,
                    COALESCE(SUM(tr.totalAmount), 0) AS totalAmount
                FROM transactions tr
                WHERE DATE(tr.transactionDate) BETWEEN '{from_date_str}' AND '{to_date_str}'
                AND tr.isVoided = 0 AND tr.isPaid = 1
                {branch_filter}
                GROUP BY DATE(tr.transactionDate)
                ORDER BY date
            """
            time_data = await connection.execute_query_dict(time_query)
        
        elements = []
        
        elements.append(Paragraph("Balay Panday Hardware Sales Report", styles['Title']))
        elements.append(Spacer(1, 0.25*inch))
        
        details = [
            [f"Branch: {branch_name}"],
            [f"Date Range: {from_date_str} to {to_date_str}"],
            [f"Report Generated: {now_sg.strftime('%Y-%m-%d %H:%M:%S')}"]
        ]
        details_table = Table(details, colWidths=[doc.width])
        details_table.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,-1), 'DejaVu'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('TEXTCOLOR', (0,0), (-1,-1), colors.black),
        ]))
        elements.append(details_table)
        elements.append(Spacer(1, 0.5*inch))
        summary_data = [
            ["Metric", "Amount"],
            ["Gross Sales", f"₱{float(summary.get('gross_sales', 0)):,.2f}"],
            ["Discounts", f"₱{float(summary.get('total_discount', 0)):,.2f}"],
            ["Net Sales", f"₱{float(summary.get('net_sales', 0)):,.2f}"],
            ["Item Cost", f"₱{float(summary.get('item_cost', 0)):,.2f}"],
            ["Gross Profit", f"₱{float(summary.get('gross_profit', 0)):,.2f}"]
        ]
        
        summary_table = Table(summary_data, colWidths=[doc.width/2]*2)
        summary_table.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,-1), 'DejaVu'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#fe6500')),
            ('TEXTCOLOR', (0,1), (-1,-1), colors.black),
            ('GRID', (0,0), (-1,-1), 1, colors.lightgrey),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 0.5*inch))
        if from_date_str == to_date_str:
            time_header = [["Hour", "Sales Amount"]]
            time_rows = [[
                f"{row['hour']}:00 {'AM' if row['hour'] < 12 else 'PM'}",
                f"₱{float(row['totalAmount']):,.2f}"
            ] for row in time_data]
        else:
            time_header = [["Date", "Sales Amount"]]
            time_rows = [[
                datetime.strptime(str(row['date']), '%Y-%m-%d').strftime('%b %d, %Y'),
                f"₱{float(row['totalAmount']):,.2f}"
            ] for row in time_data]
        
        time_table = Table(time_header + time_rows, colWidths=[doc.width/2]*2)
        time_table.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,-1), 'DejaVu'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#fe6500')),
            ('TEXTCOLOR', (0,1), (-1,-1), colors.black),
            ('GRID', (0,0), (-1,-1), 1, colors.lightgrey),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        elements.append(time_table)

        elements.append(Spacer(1, 0.5*inch))
        elements.append(Paragraph("Confidential - For Internal Use Only", styles['Center']))
        
        doc.build(elements)
        buffer.seek(0)
        return buffer
    except Exception as e:
        if 'buffer' in locals():
            buffer.close()
        raise RuntimeError(f"Failed to generate PDF: {str(e)}")