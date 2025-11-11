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
    
    def _is_metadata_line(self, line: str) -> bool:
        line_lower = line.lower().strip()
        
        metadata_patterns = [
            r'^(po\s*number|order\s*number|quote\s*number|n[uú]mero|n[oó]\.?):',
            r'^(date|fecha|order\s*date|delivery\s*date|valid\s*until):',
            r'^(phone|tel[eé]fono|mobile|cell):',
            r'^(email|e-mail|correo):',
            r'^(address|direcci[oó]n|shipping|billing):',
            r'^(vendor|supplier|proveedor|from|de):',
            r'^(bill\s*to|ship\s*to|to|para):',
            r'^(payment\s*terms|t[eé]rminos|currency|moneda):',
            r'^(authorized\s*by|signed|signature|firma):',
            r'^(subtotal|total|grand\s*total|monto|iva|tax|shipping|env[ií]o):',
            r'^(thank\s*you|gracias|regards|saludos|best\s*regards)',
            r'^\+?\d{1,4}[\s\-\(\)]?\d{1,4}[\s\-]?\d{1,4}[\s\-]?\d{1,4}[\s\-]?\d{1,4}',
            r'^[\w\.-]+@[\w\.-]+\.\w+',
            r'^(monday|tuesday|wednesday|thursday|friday|saturday|sunday|lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo)',
            r'^(january|february|march|april|may|june|july|august|september|october|november|december|enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)',
        ]
        
        for pattern in metadata_patterns:
            if re.search(pattern, line_lower):
                return True
        
        if len(line_lower) < 10 and re.search(r'^[a-z\s]+:\s*\d+', line_lower):
            return True
        
        return False
    
    def _is_valid_product_name(self, nombre: str) -> bool:
        if not nombre or len(nombre) < 3:
            return False
        
        nombre_lower = nombre.lower()
        
        invalid_patterns = [
            r'^(po\s*number|order\s*number|quote\s*number|n[uú]mero):',
            r'^(date|fecha|order\s*date):',
            r'^(phone|tel[eé]fono):',
            r'^(email|correo):',
            r'^(address|direcci[oó]n):',
            r'^(vendor|supplier|from|de):',
            r'^(bill\s*to|ship\s*to|to|para):',
            r'^(payment|currency|moneda):',
            r'^(authorized|signed|signature):',
            r'^\+?\d{1,4}',
            r'^[\w\.-]+@',
            r'^[a-z\s]{1,15}:\s*\d+$',
        ]
        
        for pattern in invalid_patterns:
            if re.search(pattern, nombre_lower):
                return False
        
        if len(nombre) < 5 and re.search(r':\s*\d+', nombre):
            return False
        
        return True
    
    def extract_products_from_text(self, text: str) -> list:
        products = []
        lines = text.split('\n')
        
        header_found = False
        table_started = False
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line or len(line) < 3:
                continue
            
            if self._is_metadata_line(line):
                continue
            
            line_lower = line.lower()
            
            if re.search(r'(item|producto|description|descripci[oó]n|art[ií]culo)', line_lower) and \
               re.search(r'(qty|quantity|cantidad|price|precio|total|unit)', line_lower):
                header_found = True
                table_started = True
                continue
            
            if table_started and (re.search(r'^[-=]+$', line) or re.search(r'^_{3,}', line)):
                continue
            
            if table_started and re.search(r'(subtotal|total|grand total|monto total|iva|tax|shipping|env[ií]o)', line_lower):
                table_started = False
                continue
            
            parts = re.split(r'\s*\|\s*|\s{2,}|\t+', line)
            parts = [p.strip() for p in parts if p.strip()]
            
            if len(parts) >= 3:
                nombre = parts[0]
                nombre = re.sub(r'^[\-\*\•\>\d\.\s]+', '', nombre).strip()
                
                if not self._is_valid_product_name(nombre):
                    continue
                
                numbers = []
                for part in parts[1:]:
                    num_match = re.search(r'[\d,]+\.?\d*', part.replace('$', '').replace(',', ''))
                    if num_match:
                        try:
                            num_val = float(num_match.group(0).replace(',', ''))
                            if num_val > 0:
                                numbers.append(num_val)
                        except:
                            continue
                
                if len(numbers) >= 2:
                    try:
                        cantidad = int(numbers[0]) if numbers[0] < 10000 else int(numbers[0] / 100)
                        precio_unitario = numbers[1] if numbers[1] < 100000 else numbers[1] / 100
                        
                        if len(numbers) >= 3:
                            total = numbers[2] if numbers[2] < 1000000 else numbers[2] / 100
                        else:
                            total = cantidad * precio_unitario
                        
                        if cantidad > 0 and cantidad < 10000 and precio_unitario > 0 and precio_unitario < 100000:
                            products.append({
                                "nombre": nombre[:100],
                                "cantidad": cantidad,
                                "precio_unitario": round(precio_unitario, 2),
                                "total": round(total, 2)
                            })
                            continue
                    except:
                        pass
            
            numbers = re.findall(r'[\d,]+\.?\d*', line)
            if len(numbers) >= 2:
                try:
                    nombre = re.sub(r'[\d,]+\.?\d*.*$', '', line).strip()
                    nombre = re.sub(r'^[\-\*\•\>\s]+', '', nombre).strip()
                    
                    if not self._is_valid_product_name(nombre):
                        continue
                    
                    nums = []
                    for n in numbers:
                        try:
                            num_val = float(n.replace(',', ''))
                            if num_val > 0:
                                nums.append(num_val)
                        except:
                            continue
                    
                    if len(nums) >= 2:
                        cantidad = int(nums[0]) if nums[0] < 10000 else int(nums[0] / 100)
                        precio_unitario = nums[1] if nums[1] < 100000 else nums[1] / 100
                        
                        if len(nums) >= 3:
                            total = nums[2] if nums[2] < 1000000 else nums[2] / 100
                        else:
                            total = cantidad * precio_unitario
                        
                        if cantidad > 0 and cantidad < 10000 and precio_unitario > 0 and precio_unitario < 100000:
                            products.append({
                                "nombre": nombre[:100],
                                "cantidad": cantidad,
                                "precio_unitario": round(precio_unitario, 2),
                                "total": round(total, 2)
                            })
                            continue
                except (ValueError, IndexError):
                    pass
            
            qty_match = re.search(r'(?:Qty|Quantity|Cantidad|Cant)[\s:]*(\d+)', line, re.IGNORECASE)
            price_match = re.search(r'(?:Price|Precio|Unit|Unitario|P\.U\.)[\s:]*\$?\s*([\d,]+\.?\d*)', line, re.IGNORECASE)
            
            if qty_match and price_match:
                nombre_part = re.sub(r'(?:Qty|Quantity|Cantidad|Price|Precio|Unit|Unitario|P\.U\.).*', '', line, flags=re.IGNORECASE).strip()
                if not nombre_part or len(nombre_part) < 2:
                    if i > 0:
                        prev_line = lines[i-1].strip()
                        if prev_line and len(prev_line) > 2:
                            nombre_part = prev_line[:100]
                
                nombre_part = nombre_part or "Producto sin nombre"
                nombre_part = re.sub(r'^[\-\*\•\>\s]+', '', nombre_part).strip()
                
                if not self._is_valid_product_name(nombre_part):
                    continue
                
                try:
                    cantidad = int(qty_match.group(1))
                    precio_unitario = float(price_match.group(1).replace(',', ''))
                    
                    if cantidad > 0 and cantidad < 10000 and precio_unitario > 0 and precio_unitario < 100000:
                        products.append({
                            "nombre": nombre_part[:100],
                            "cantidad": cantidad,
                            "precio_unitario": round(precio_unitario, 2),
                            "total": round(cantidad * precio_unitario, 2)
                        })
                except:
                    pass
        
        seen = set()
        unique_products = []
        for p in products:
            key = (p["nombre"].lower(), p["cantidad"], p["precio_unitario"])
            if key not in seen:
                seen.add(key)
                unique_products.append(p)
        
        return unique_products
    
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

