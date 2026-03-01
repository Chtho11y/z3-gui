import re
from enum import Enum
from typing import List, Optional, Union

class TokenType(Enum):
    NUMBER = 'NUMBER'        # 数字（整数）
    SYMBOL = 'SYMBOL'         # 符号（多字符符号）
    KEYWORD = 'KEYWORD'       # 关键字（纯字母）
    VAR = 'VAR'              # 变量（字母/汉字开头+数字）
    ANNOTATION = 'ANNOTATION' # 注解（@开头的变量名）
    WHITESPACE = 'WHITESPACE' # 空白字符
    UNKNOWN = 'UNKNOWN'       # 未知字符

class Token:
    def __init__(self, token_type: TokenType, value: str, line: int, column: int):
        self.type = token_type
        self.value = value
        self.line = line
        self.column = column
    
    def __repr__(self):
        return f"Token({self.type}, '{self.value}', line={self.line}, col={self.column})"

class Tokenizer:
    def __init__(self, symbols: List[str], keywords: List[str]):
        """
        初始化tokenizer
        
        Args:
            symbols: 符号列表，按长度降序排列（用于贪心匹配）
            keywords: 关键字列表
        """
        # 确保符号按长度降序排列，实现贪心匹配
        self.symbols = sorted(symbols, key=len, reverse=True)
        self.keywords = set(keywords)
        
        # 构建正则表达式模式
        self._build_patterns()
    
    def _build_patterns(self):
        """构建用于tokenization的正则表达式模式"""
        patterns = []
        
        # 1. 注解模式：@开头，后跟变量名（字母/汉字开头，可包含数字）
        patterns.append(r'@[a-zA-Z\u4e00-\u9fff][a-zA-Z0-9\u4e00-\u9fff]*')
        
        # 2. 符号模式：贪心匹配，需要转义特殊字符
        escaped_symbols = [re.escape(s) for s in self.symbols]
        if escaped_symbols:
            patterns.append('|'.join(escaped_symbols))
        
        # 3. 数字模式：纯数字（不含小数）
        patterns.append(r'\d+')
        
        # 4. 关键字模式：纯字母
        if self.keywords:
            # 注意：关键字会被变量模式捕获，所以我们需要在变量模式之前处理
            keyword_pattern = '|'.join(re.escape(k) for k in sorted(self.keywords, key=len, reverse=True))
            patterns.append(r'\b(?:' + keyword_pattern + r')\b')
        
        # 5. 变量模式：字母/汉字开头，后跟字母/汉字/数字
        patterns.append(r'[a-zA-Z\u4e00-\u9fff][a-zA-Z0-9\u4e00-\u9fff]*')
        
        # 6. 空白字符
        patterns.append(r'\s+')
        
        # 组合所有模式
        self.pattern = re.compile('|'.join(patterns))
        
        # 用于处理未知字符的模式
        self.unknown_pattern = re.compile(r'.')
    
    def tokenize(self, text: str) -> List[Token]:
        """
        将输入文本转换为token列表
        """
        tokens = []
        pos = 0
        line = 1
        line_start = 0
        length = len(text)
        
        while pos < length:
            # 检查当前位置开始的匹配
            match = self.pattern.match(text, pos)
            
            if match:
                value = match.group()
                token_type = self._determine_token_type(value)
                
                # 计算列号
                column = pos - line_start + 1
                
                # 添加token（跳过空白字符）
                if token_type != TokenType.WHITESPACE:
                    tokens.append(Token(token_type, value, line, column))
                
                # 更新位置
                pos = match.end()
                
                # 更新行号
                line += value.count('\n')
                if '\n' in value:
                    line_start = pos - (len(value) - value.rfind('\n') - 1)
            else:
                # 处理未知字符
                unknown_char = text[pos]
                column = pos - line_start + 1
                tokens.append(Token(TokenType.UNKNOWN, unknown_char, line, column))
                
                # 更新位置
                if unknown_char == '\n':
                    line += 1
                    line_start = pos + 1
                pos += 1
        
        return tokens
    
    def _determine_token_type(self, value: str) -> TokenType:
        """根据token值确定其类型"""
        if value.startswith('@'):
            return TokenType.ANNOTATION
        elif value in self.symbols:
            return TokenType.SYMBOL
        elif value.isdigit():
            return TokenType.NUMBER
        elif value in self.keywords:
            return TokenType.KEYWORD
        elif re.match(r'^[a-zA-Z\u4e00-\u9fff][a-zA-Z0-9\u4e00-\u9fff]*$', value):
            return TokenType.VAR
        elif value.isspace():
            return TokenType.WHITESPACE
        else:
            return TokenType.UNKNOWN

# 使用示例
def demo():
    # 定义符号列表（按长度降序排列）
    symbols = [
        '=', '>=', '<=', '==', '!=', '&&', '||',
        '+', '-', '*', '/', '=', '<', '>', '!', '(', ')', '{', '}', '[', ']', ';', ',', '.'
    ]
    
    # 定义关键字列表
    keywords = ['for', 'in']
    
    # 创建tokenizer
    tokenizer = Tokenizer(symbols, keywords)
    
    # 测试文本
    test_text = """
    @sudoku(X, 9)
    for i in row(reg1):
        sum(X[i]) == 45
    """
    
    # 进行tokenization
    tokens = tokenizer.tokenize(test_text)
    
    # 打印结果
    print("输入文本:")
    print(test_text)
    print("\n解析结果:")
    for token in tokens:
        print(token)
    
    # 也可以按行查看
    print("\n按行查看:")
    current_line = 1
    for token in tokens:
        if token.line > current_line:
            print()  # 空行分隔
            current_line = token.line
        print(f"  L{token.line}:{token.column} {token.type.value:12} '{token.value}'")

if __name__ == "__main__":
    demo()