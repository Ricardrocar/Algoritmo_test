import re
from typing import Dict, Any, Optional


class ClassificationService:
    
    def classify_document(self, subject: str, body: str, pdf_text: str = "") -> str:
        subject_upper = subject.upper()
        body_upper = body.upper()
        pdf_upper = pdf_text.upper()
        combined_text = f"{subject} {body} {pdf_text}"
        
        has_po = False
        has_quote = False
        
        po_patterns_subject = [
            r'\bPO\b',
            r'\bPURCHASE\s+ORDER\b',
            r'\bORDEN\s+DE\s+COMPRA\b',
            r'\bORDEN\s*#',
            r'\bPO[-_\s]?\d+'
        ]
        
        for pattern in po_patterns_subject:
            if re.search(pattern, subject_upper):
                return "PO"
        
        quote_patterns = [
            r'\bQUOTE\b',
            r'\bQUOTATION\b',
            r'\bCOTIZACI[OÓ]N\b',
            r'\bQUOTE\s+REQUEST\b'
        ]
        
        for pattern in quote_patterns:
            if re.search(pattern, subject_upper) or re.search(pattern, body_upper):
                has_quote = True
                break
        
        if pdf_text:
            pdf_po_patterns = [
                r'\bPURCHASE\s+ORDER\b',
                r'\bPO\s+NUMBER\b',
                r'\bPO\s*#'
            ]
            
            for pattern in pdf_po_patterns:
                if re.search(pattern, pdf_upper):
                    if not has_quote:
                        return "PO"
                    has_po = True
                    break
        
        quote_request_patterns = [
            r'\bSEND\s+ME\s+A\s+QUOTE\b',
            r'\bCOTIZACI[OÓ]N\b',
            r'\bPLEASE\s+QUOTE\b',
            r'\bQUOTE\s+FOR\b',
            r'\bPRICE\s+QUOTE\b',
            r'\bREQUEST.*QUOTE\b',
            r'\bSOLICIT(O|A|AR).*COTIZACI[OÓ]N\b',
            r'\bCONFIRM(AR|A|O).*PRECIO(S)?\b'
        ]
        
        po_number_patterns = [
            r'\bPO\s*[-:#]?\s*\d+',
            r'\bORDEN\s*[-:#]?\s*\d+',
            r'\bORDER\s*[-:#]?\s*\d+'
        ]
        
        has_po_number = False
        for pattern in po_number_patterns:
            if re.search(pattern, combined_text, re.IGNORECASE):
                has_po_number = True
                break
        
        for pattern in quote_request_patterns:
            if re.search(pattern, combined_text.upper()):
                if not has_po_number:
                    return "QUOTE"
                has_quote = True
                break
        
        if has_po and has_quote:
            if has_po_number:
                return "PO"
            else:
                return "QUOTE"
        
        if has_po:
            return "PO"
        elif has_quote:
            return "QUOTE"
        else:
            return "UNKNOWN"
    
    def extract_products_from_text(self, text: str) -> list:
        products = []
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line or len(line) < 5:
                continue
            
            numbers = re.findall(r'[\d,]+\.?\d*', line)
            if len(numbers) >= 2:
                try:
                    nombre = re.sub(r'[\d,]+\.?\d*.*$', '', line).strip()
                    nombre = re.sub(r'^[\-\*\•\>\s]+', '', nombre).strip()
                    
                    if len(nombre) < 2:
                        continue
                    
                    nums = [float(n.replace(',', '')) for n in numbers if n.replace(',', '').replace('.', '').isdigit()]
                    
                    if len(nums) >= 3:
                        cantidad = int(nums[0])
                        precio_unitario = nums[1]
                        total = nums[2]
                    elif len(nums) == 2:
                        cantidad = int(nums[0])
                        precio_unitario = nums[1]
                        total = cantidad * precio_unitario
                    else:
                        continue
                    
                    if cantidad > 0 and precio_unitario > 0:
                        products.append({
                            "nombre": nombre[:100],
                            "cantidad": cantidad,
                            "precio_unitario": round(precio_unitario, 2),
                            "total": round(total, 2)
                        })
                except (ValueError, IndexError):
                    continue
            
            qty_match = re.search(r'(?:Qty|Quantity|Cantidad|Cant)[\s:]*(\d+)', line, re.IGNORECASE)
            price_match = re.search(r'(?:Price|Precio|Unit|Unitario)[\s:]*\$?\s*([\d,]+\.?\d*)', line, re.IGNORECASE)
            
            if qty_match and price_match:
                nombre_part = re.sub(r'(?:Qty|Quantity|Cantidad|Price|Precio|Unit).*', '', line, flags=re.IGNORECASE).strip()
                if not nombre_part and i > 0:
                    nombre_part = lines[i-1].strip()[:100]
                
                nombre_part = nombre_part or "Producto sin nombre"
                cantidad = int(qty_match.group(1))
                precio_unitario = float(price_match.group(1).replace(',', ''))
                
                products.append({
                    "nombre": nombre_part[:100],
                    "cantidad": cantidad,
                    "precio_unitario": round(precio_unitario, 2),
                    "total": round(cantidad * precio_unitario, 2)
                })
        
        return products
    
    def extract_totals_from_text(self, text: str) -> Dict[str, Any]:
        totals = {"total": 0.0, "moneda": "USD"}
        
        currency_patterns = [
            r'\b(USD|EUR|GBP|MXN|COP|ARS|CLP|PEN|BRL)\b',
            r'(?:Currency|Moneda|Divisa)[\s:]+(\w+)',
            r'\$\s*(?:USD|EUR|GBP|MXN|COP)',
            r'(?:USD|EUR|GBP|MXN|COP)\s*\$'
        ]
        
        for pattern in currency_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                currency = match.group(1) if match.group(1) else match.group(0)
                currency_code = re.findall(r'[A-Z]{3}', currency.upper())
                if currency_code:
                    totals["moneda"] = currency_code[0]
                    break
        
        total_patterns = [
            r'(?:Total|Grand Total|Amount Due|Monto Total|Total Amount|Net Total|Final Total)[\s:]*\$?\s*([\d,]+\.?\d*)',
            r'(?:Total)[\s:]*(?:USD|EUR|GBP|MXN|COP)?\s*\$?\s*([\d,]+\.?\d*)',
            r'\$\s*([\d,]+\.?\d*)\s*(?:USD|EUR|GBP|MXN|COP)?',
            r'(?:^|\n)\s*Total[\s:]*[\$]?\s*([\d,]+\.?\d*)'
        ]
        
        for pattern in total_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                try:
                    total_value = float(match.group(1).replace(',', ''))
                    if total_value > 0:
                        totals["total"] = round(total_value, 2)
                        break
                except (ValueError, IndexError):
                    continue
        
        return totals

_classification_service_instance: Optional[ClassificationService] = None
def get_classification_service() -> ClassificationService:
    global _classification_service_instance
    if _classification_service_instance is None:
        _classification_service_instance = ClassificationService()
    return _classification_service_instance

