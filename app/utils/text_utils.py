import re
import html
from html.parser import HTMLParser


class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.in_table = False
        self.in_list = False
        self.current_line = []
        
    def handle_data(self, data):
        if data.strip():
            self.current_line.append(data.strip())
    
    def handle_starttag(self, tag, attrs):
        if tag in ['table', 'tbody', 'thead']:
            self.in_table = True
        elif tag in ['ul', 'ol']:
            self.in_list = True
        elif tag in ['tr', 'li', 'br', 'p', 'div']:
            if self.current_line:
                line = ' '.join(self.current_line).strip()
                if line:
                    self.text.append(line)
                self.current_line = []
    
    def handle_endtag(self, tag):
        if tag in ['table', 'tbody', 'thead']:
            self.in_table = False
        elif tag in ['ul', 'ol']:
            self.in_list = False
        elif tag in ['tr', 'li', 'p', 'div']:
            if self.current_line:
                line = ' '.join(self.current_line).strip()
                if line:
                    self.text.append(line)
                self.current_line = []
    
    def get_text(self):
        if self.current_line:
            line = ' '.join(self.current_line).strip()
            if line:
                self.text.append(line)
        return '\n'.join(self.text)


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)
    return text


def html_to_text(html_content: str) -> str:
    if not html_content:
        return ""
    
    html_content = html.unescape(html_content)
    
    html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    html_content = re.sub(r'<noscript[^>]*>.*?</noscript>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    
    parser = HTMLTextExtractor()
    try:
        parser.feed(html_content)
        text = parser.get_text()
    except:
        text = re.sub(r'<[^>]+>', ' ', html_content)
    
    text = re.sub(r'\n\s*\n', '\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = clean_text(text)
    
    return text


def truncate_text(text: str, max_length: int = 100) -> str:
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."

