import re
from typing import Dict, Any, Optional


class ClassificationService:
    """Servicio para clasificar documentos como PO o QUOTE."""
    
    def classify_document(self, subject: str, body: str, pdf_text: str = "") -> str:
        """ Clasificacion de PO o QUOTE """
        combined_text = f"{subject} {body} {pdf_text}".upper()
        has_po, has_quote = False, False
        
        # REGLA 1: PO en asunto
        po_subject = r'\b(PO|Purchase Order|Orden de Compra|Orden\s*#|PO[-_\s]?\d+)\b'
        if re.search(po_subject, subject, re.IGNORECASE):
            return "PO"
        
        # REGLA 2: QUOTE en asunto o cuerpo
        quote_pattern = r'\b(QUOTE|Quotation|Cotización|Quote Request)\b'
        if re.search(quote_pattern, subject + body, re.IGNORECASE):
            has_quote = True
        
        # REGLA 3: PO en PDF
        if pdf_text and re.search(r'\b(Purchase Order|PO Number)\b', pdf_text, re.IGNORECASE):
            if not has_quote:
                return "PO"
            has_po = True
        
        # REGLA 4: QUOTE si solicita precios sin número de PO
        quote_request = r'(send me a quote|cotizaci[oó]n|please quote|quote for|price quote|request.*quote)'
        po_number = r'\b(PO|Orden|Order)\s*[-:#]?\s*\d+'
        if re.search(quote_request, combined_text, re.IGNORECASE):
            if not re.search(po_number, combined_text, re.IGNORECASE):
                return "QUOTE"
            has_quote = True
        
        # REGLA 5: Desempate
        if has_po and has_quote:
            return "PO" if re.search(po_number, combined_text, re.IGNORECASE) else "QUOTE"
        
        return "PO" if has_po else "QUOTE" if has_quote else "UNKNOWN"
    
    def extract_products_from_text(self, text: str) -> list:
        """Extraer productos del texto con patrones flexibles."""
        products = []
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line or len(line) < 5:
                continue
            
            # Buscar todos los números en la línea
            numbers = re.findall(r'[\d,]+\.?\d*', line)
            if len(numbers) >= 2:
                try:
                    # Extraer nombre (texto antes de los números)
                    nombre = re.sub(r'[\d,]+\.?\d*.*$', '', line).strip()
                    
                    # Limpiar nombre de caracteres especiales al inicio
                    nombre = re.sub(r'^[\-\*\•\>\s]+', '', nombre).strip()
                    
                    if len(nombre) < 2:
                        continue
                    
                    # Intentar diferentes combinaciones de números
                    nums = [float(n.replace(',', '')) for n in numbers if n.replace(',', '').replace('.', '').isdigit()]
                    
                    if len(nums) >= 3:
                        # Formato: nombre cantidad precio_unitario total
                        cantidad = int(nums[0])
                        precio_unitario = nums[1]
                        total = nums[2]
                    elif len(nums) == 2:
                        # Formato: nombre cantidad precio (calcular total)
                        cantidad = int(nums[0])
                        precio_unitario = nums[1]
                        total = cantidad * precio_unitario
                    else:
                        continue
                    
                    if cantidad > 0 and precio_unitario > 0:
                        products.append({
                            "nombre": nombre[:100],  # Limitar longitud
                            "cantidad": cantidad,
                            "precio_unitario": round(precio_unitario, 2),
                            "total": round(total, 2)
                        })
                except (ValueError, IndexError):
                    continue
            
            # Patrón específico: "Qty: X, Price: Y" o similar
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
        """Extraer totales y moneda del texto con patrones flexibles."""
        totals = {"total": 0.0, "moneda": "USD"}
        
        # Buscar moneda primero (aparece frecuentemente antes del total)
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
                # Extraer solo las letras de moneda
                currency_code = re.findall(r'[A-Z]{3}', currency.upper())
                if currency_code:
                    totals["moneda"] = currency_code[0]
                    break
        
        # Buscar total con múltiples patrones
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


# Instancia global
_classification_service_instance: Optional[ClassificationService] = None


def get_classification_service() -> ClassificationService:
    """Obtener o crear instancia del servicio de clasificación."""
    global _classification_service_instance
    if _classification_service_instance is None:
        _classification_service_instance = ClassificationService()
    return _classification_service_instance

