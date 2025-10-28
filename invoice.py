import json
import os
import re
from decimal import Decimal

import psycopg2
import psycopg2.extras

from db import get_db_connection
from fastapi import HTTPException

from decimal import Decimal, InvalidOperation

def parse_decimal(value):
    if value is None:
        return Decimal("0.00")
    if isinstance(value, (int, float, Decimal)):
        return Decimal(value)
    try:
        cleaned = str(value).replace(",", "").replace("₹", "").strip()
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return Decimal("0.00")

def parse_date(value):
    from datetime import datetime
    if not value:
        return None
    for fmt in ("%d/%m/%Y", "%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except:
            continue
    return None

def clean_gstin(value):
    if not value:
        return ""
    if "GSTIN" in value:
        return value.split(":")[-1].strip()
    return value.strip()

# def process_invoice_json_output(file_path):
#     with open(file_path, 'r') as file:
#         text_data = file.read()

#     clean_text = re.sub(r'<.*?>', '', text_data)
#     json_start = clean_text.find('{')
#     json_end = clean_text.rfind('}') + 1
#     json_string = clean_text[json_start:json_end]

#     try:
#         json_data = json.loads(json_string)
#     except json.JSONDecodeError as e:
#         raise HTTPException(status_code=500, detail=f"Error decoding JSON: {e}")

#     return json_data

def extract_first_element(temp_dict):
    return [{k: (v[0] if isinstance(v, tuple) else v) for k, v in temp_dict.items()}]

def filter_dict_based_on_empty_values(dict_list):
    return [d for d in dict_list if sum(1 for v in d.values() if v == '') <= 2]

def insert_invoice_data(json_data,insert_id=None):
    print("insert invoice data")
    print(insert_id,"+++++++++++++++++++++++++++++")
    extracted_data = json_data
    summary_data = []

    if extracted_data:
        # file = os.path.basename(file_path)
        temp_dict = {}
        temp_dict["invoice_number"] = extracted_data.get("invoice_number", "")
        temp_dict["invoice_date"] = parse_date(extracted_data.get("invoice_date", ""))
        temp_dict["total_amount"] = parse_decimal(extracted_data.get("total_amount", "0"))
        temp_dict["po_ref"] = extracted_data.get("po_ref", "")
        temp_dict["company_name"] = extracted_data.get("company_name", "")
        temp_dict["vendor_name"] = extracted_data.get("supplier_name", "")
        temp_dict["supplier_gstin"] = clean_gstin(extracted_data.get("gstin_supplier", ""))
        temp_dict["buyer_gstin"] = clean_gstin(extracted_data.get("bill_to_gstin", ""))
        temp_dict["delivery_location"] = extracted_data.get("bill_to_address", "")
        temp_dict["batch_id"] = insert_id
        # temp_dict["file_name"] = file

        summary_data.append(temp_dict)

        conn = get_db_connection()
        cur = conn.cursor()

        table_name = 'invoice_details'
        columns = ', '.join(temp_dict.keys())
        values = ', '.join(['%s'] * len(temp_dict))

        cleaned_data = extract_first_element(temp_dict)

        try:
            temp_data = filter_dict_based_on_empty_values(cleaned_data)
            if len(temp_data) > 0:
                insert_query = f'INSERT INTO {table_name} ({columns}) VALUES ({values}) RETURNING invoice_id'
                cur.execute(insert_query, list(temp_data[0].values()))
                invoice_id = cur.fetchone()[0]

                # Insert line items if invoice insert succeeded
                line_items = extracted_data.get("line_items", [])
                for item in line_items:
                    item_dict = {
                        "item_name": item.get("item_name", ""),
                        "hsn": item.get("hsn", ""),
                        "quantity": parse_decimal(item.get("item_qty", "0")),
                        "uom": item.get("uom", ""),
                        "rate_incl_of_tax": parse_decimal(item.get("rate_incl_of_tax", "0")),
                        "unit_price": parse_decimal(item.get("unit_price", "0")),
                        "total_retail_price": parse_decimal(item.get("total_retail_price", "0")),
                        "total_taxable_amount": parse_decimal(item.get("total_taxable_amount", "0")),
                        "discount": parse_decimal(item.get("discount", "0")),
                        "total_value": parse_decimal(item.get("total_value", "0")),
                        "invoice_id": invoice_id
                       
                    }

                    lineitem_columns = ', '.join(item_dict.keys())
                    lineitem_values = ', '.join(['%s'] * len(item_dict))

                    line_query = f"INSERT INTO invoice_lineitems ({lineitem_columns}) VALUES ({lineitem_values})"
                    cur.execute(line_query, list(item_dict.values()))
                
                # 🔄 Update status based on po_ref value
                # if insert_id:
                #     status = "Reconciliation" if temp_data[0]["po_ref"] else "Po No not mapped"
                #     cur.execute("""
                #         UPDATE pdf_conversion_hypotus
                #         SET status = %s
                #         WHERE id = %s
                #     """, (status, insert_id))
                if insert_id:
                    po_ref = temp_data[0]["po_ref"]

                    if po_ref:
                        # Run the checklist function
                        cur_1 = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                        cur_1.execute("SELECT * FROM generate_invoice_checklist(%s)", (invoice_id,))
                        row = cur_1.fetchone()
                        print("row", row)
                        # Check the overall_status result
                        if row and row["overall_status"] == "no match":
                            status = "Checklist Failed"
                        else:
                            status = "Reconciliation"
                    else:
                        status = "Po No not mapped"

                    # Update the status in DB
                    cur.execute("""
                        UPDATE pdf_conversion_hypotus
                        SET status = %s
                        WHERE id = %s
                    """, (status, insert_id))
                    conn.commit()

        except Exception as e:
            print("❌ Error inserting:", e)
            conn.rollback()

        conn.commit()
        cur.close()
        conn.close()
        print(f"✅ Inserted invoice id: {invoice_id}")
        return status
    else:
        print(f"✅ not insertred invoice id: {invoice_id}")


def insert_po_data(json_data, insert_id=None):
    print("🔄 Inside insert_po_data")
    extracted_data = json_data
    po_id = None
    status = "No data to insert"

    if extracted_data:
        temp_dict = {
            "po_number": extracted_data.get("po_ref", ""),
            "po_date": parse_date(extracted_data.get("invoice_date", "")),
            "total_amount": parse_decimal(extracted_data.get("total_invoice_value", "0")),
            "vendor_ref": extracted_data.get("invoice_id", ""),
            "shipment_mode": extracted_data.get("shipment_mode", "By Transport"),
            "supplier_pan": extracted_data.get("pan_supplier", ""),
            "supplier_gstin": clean_gstin(extracted_data.get("gstin_supplier", "")),
            "buyer_gstin": clean_gstin(extracted_data.get("bill_to_gstin", "")),
            "delivery_location": extracted_data.get("ship_to_address", "")[:255],
            "vendor_name": extracted_data.get("supplier_name", ""),
            "po_status": "open",
            "item_code": ""  # placeholder, overwritten per item
        }

        conn = get_db_connection()
        cur = conn.cursor()

        table_name = 'po_details'
        columns = ', '.join(temp_dict.keys())
        values = ', '.join(['%s'] * len(temp_dict))
        cleaned_data = extract_first_element(temp_dict)

        try:
            temp_data = filter_dict_based_on_empty_values(cleaned_data)
            if len(temp_data) > 0:
                insert_query = f'INSERT INTO {table_name} ({columns}) VALUES ({values}) RETURNING po_id'
                cur.execute(insert_query, list(temp_data[0].values()))
                po_id = cur.fetchone()[0]

                # ✅ Insert PO Line Items
                line_items = extracted_data.get("line_items", [])
                for item in line_items:
                    item_dict = {
                        "po_id": po_id,
                        "item_name": item.get("item_name", ""),
                        "oem_part_code": item.get("oem_part_code", "")[:100] if item.get("oem_part_code") else "",
                        "quantity": parse_decimal(item.get("item_qty", "0")),
                        "uom": item.get("uom", "")[:50] or "Nos",
                        "unit_price": parse_decimal(item.get("unit_price", "0")),
                        "discount": parse_decimal(item.get("discount", "0")),
                        "taxable": parse_decimal(item.get("total_taxable_amount", "0")),
                        "gst_rate": parse_decimal(extracted_data.get("gst_rate", "0.00")),
                        "gst_amount": parse_decimal(extracted_data.get("total_tax_amount", "0")),
                        "billable_value": parse_decimal(item.get("total_value", "0")),
                        "total_qty": parse_decimal(extracted_data.get("total_quantity", "0")),
                        "cgst": parse_decimal(extracted_data.get("total_cgst_amount", "0")),
                        "sgst": parse_decimal(extracted_data.get("total_sgst_amount", "0")),
                        "igst": parse_decimal(extracted_data.get("total_igst_amount", "0") or "0"),
                        "gross_amount": parse_decimal(extracted_data.get("total_invoice_value", "0"))
                    }

                    # Optional: update item_code in po_details
                    cur.execute("UPDATE po_details SET item_code = %s WHERE po_id = %s",
                                (item_dict["item_name"], po_id))

                    lineitem_columns = ', '.join(item_dict.keys())
                    lineitem_values = ', '.join(['%s'] * len(item_dict))
                    line_query = f"INSERT INTO po_lineitems ({lineitem_columns}) VALUES ({lineitem_values})"
                    cur.execute(line_query, list(item_dict.values()))

                # ✅ Update status in pdf_conversion_hypotus
                # if insert_id:
                #     po_number = temp_data[0].get("po_number", "")
                #     status = "Po No not mapped" if not po_number else "Reconciliation"

                #     cur.execute("""
                #         UPDATE pdf_conversion_hypotus
                #         SET status = %s
                #         WHERE id = %s
                #     """, (status, insert_id))

                conn.commit()
        except Exception as e:
            print("❌ Error inserting PO:", e)
            conn.rollback()
            status = "Insert failed"
        finally:
            cur.close()
            conn.close()

        print(f"✅ Inserted PO id: {po_id}")
        return status if po_id else "Insert failed"
    else:
        print("⚠️ No PO data found to insert")
        return "No data to insert"

    
def insert_ewaybill_data(json_data, insert_id=None):
    print("🔄 Inserting eWayBill data...")
    extracted_data = json_data
    status = "No data to insert"

    if extracted_data:
        temp_dict = {
            "ewaybill_no": extracted_data.get("ewaybill_no", ""),
            "ewaybill_date": parse_date(extracted_data.get("ewaybill_date", "")),
            "generated_by": extracted_data.get("generated_by", ""),
            "irn": extracted_data.get("irn", ""),
            "gstin_supplier": clean_gstin(extracted_data.get("gstin_supplier", "")),
            "vendor_name": extracted_data.get("vendor_name", ""),
            "place_of_dispatch": extracted_data.get("place_of_dispatch", ""),
            "gstin_recipient": clean_gstin(extracted_data.get("gstin_recipient", "")),
            "client_name": extracted_data.get("client_name", ""),
            "place_of_delivery": extracted_data.get("place_of_delivery", ""),
            "document_no": extracted_data.get("document_no", ""),
            "document_date": parse_date(extracted_data.get("document_date", "")),
            "value_of_goods": parse_decimal(extracted_data.get("value_of_goods", "0")),
            "hsn_code": extracted_data.get("hsn_code", ""),
            "transporter": extracted_data.get("transporter", "")
        }

        try:
            conn = get_db_connection()
            cur = conn.cursor()

            table_name = 'ewaybill_details'
            columns = ', '.join(temp_dict.keys())
            values = ', '.join(['%s'] * len(temp_dict))
            insert_query = f'INSERT INTO {table_name} ({columns}) VALUES ({values}) RETURNING id'

            cur.execute(insert_query, list(temp_dict.values()))
            ewaybill_id = cur.fetchone()[0]

            # Optional: Update status in pdf_conversion_hypotus if insert_id is passed
            if insert_id:
                status = "Reconciliation" if temp_dict["ewaybill_no"] else "E-way bill No not mapped"

                cur.execute("""
                    UPDATE pdf_conversion_hypotus
                    SET status = %s
                    WHERE id = %s
                """, (status, insert_id))

                if temp_dict["ewaybill_no"]:
                    cur_1 = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                    cur_1.execute("SELECT * FROM compare_invoice_ewaybill_by_number(%s)", (temp_dict["document_no"],))
                    row = cur_1.fetchone()
                    if row and row["overall_status"] == "no match":
                        status = "Checklist Failed"
                    else:
                        status = "Reconciliation"

                    # Final update after checklist
                    cur.execute("""
                        UPDATE pdf_conversion_hypotus
                        SET status = %s
                        WHERE id = %s
                    """, (status, insert_id))

            conn.commit()
            cur.close()
            conn.close()
            print(f"✅ Inserted E-way bill with ID: {ewaybill_id}")
            return status

        except Exception as e:
            print("❌ Error inserting eWayBill data:", e)
            conn.rollback()
            return "Insert failed"
    else:
        print("⚠️ No eWayBill data to insert.")
        return status
