"""
技能内容安全扫描器
检测潜在的注入攻击、恶意提示词和不安全内容
"""
import re
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class SecurityIssue:
    """安全问题描述"""
    severity: str  # 'critical', 'high', 'medium', 'low', 'info'
    category: str  # 'sql_injection', 'prompt_injection', 'xss', 'command_injection', 'malicious_url', 'excessive_length'
    description: str
    matched_pattern: str
    position: int  # 在内容中的位置


@dataclass
class ScanResult:
    """扫描结果"""
    is_safe: bool
    security_score: float  # 0-100分，100分最安全
    issues: List[SecurityIssue]
    warnings: List[str]
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'is_safe': self.is_safe,
            'security_score': self.security_score,
            'issues': [
                {
                    'severity': issue.severity,
                    'category': issue.category,
                    'description': issue.description,
                    'matched_pattern': issue.matched_pattern[:50],  # 截断显示
                    'position': issue.position
                }
                for issue in self.issues
            ],
            'warnings': self.warnings
        }


class SkillSecurityScanner:
    """技能安全扫描器"""
    
    # 严重程度分数
    SEVERITY_SCORES = {
        'critical': 50,
        'high': 30,
        'medium': 15,
        'low': 5,
        'info': 0
    }
    
    # SQL注入模式
    SQL_INJECTION_PATTERNS = [
        r"(?i)(union\s+select|insert\s+into|delete\s+from|drop\s+table|update\s+.*\s+set)",
        r"(?i)(exec\(|execute\(|eval\()",
        r"(?i)(;.*--|'.*or.*'.*=.*'|1.*=.*1)",
        r"(?i)(xp_cmdshell|sp_executesql)"
    ]
    
    # 命令注入模式
    COMMAND_INJECTION_PATTERNS = [
        r"(?i)(\||&&|;)\s*(wget|curl|rm|bash|sh|powershell)",  # 更精确的模式
        r"(?i)(wget|curl|nc|netcat)\s+http",
        r"(?i)(rm\s+-rf|del\s+/[fsq]|format\s+[a-z]:)"
    ]
    
    # Prompt注入模式
    PROMPT_INJECTION_PATTERNS = [
        r"(?i)(ignore\s+(previous|all|above)\s+(instructions?|prompts?|commands?|rules?))",
        r"(?i)(disregard|forget|override)\s+(previous|all|above)",
        r"(?i)(you\s+are\s+now|from\s+now\s+on|new\s+instructions?)",
        r"(?i)(system\s*:\s*|assistant\s*:\s*|user\s*:\s*).*(\n|$)",
        r"(?i)(reveal|show|print|output)\s+(your|the)\s+(prompt|instructions?|system\s+message)",
        r"(?i)(jailbreak|DAN\s+mode|developer\s+mode)"
    ]
    
    # XSS模式
    XSS_PATTERNS = [
        r"(?i)(<script[^>]*>.*?</script>)",
        r"(?i)(javascript:)",
        r"(?i)(on\w+\s*=\s*['\"])",
        r"(?i)(<iframe|<embed|<object)"
    ]
    
    # 恶意URL模式
    MALICIOUS_URL_PATTERNS = [
        r"(?i)(http://.*\.(ru|cn|tk)/)",  # 高风险TLD
        r"(?i)(phishing|malware|virus|trojan)",
        r"(?i)(bit\.ly|tinyurl|goo\.gl)/[a-zA-Z0-9]{5,}"  # 短链接（可能隐藏恶意链接）
    ]
    
    # 敏感关键词
    SENSITIVE_KEYWORDS = [
        'password', 'api_key', 'secret', 'token', 'private_key',
        'credit_card', 'ssn', 'social_security'
    ]
    
    # 内容长度限制（字符）
    MAX_CONTENT_LENGTH = 100000  # 100KB
    MAX_LINE_LENGTH = 10000
    
    def __init__(self, strict_mode: bool = False):
        """
        初始化扫描器
        
        Args:
            strict_mode: 严格模式（更严格的检查规则）
        """
        self.strict_mode = strict_mode
    
    def scan_content(self, content: str, metadata: Dict = None) -> ScanResult:
        """
        扫描技能内容
        
        Args:
            content: 技能内容
            metadata: 技能元数据
        
        Returns:
            ScanResult: 扫描结果
        """
        issues = []
        warnings = []
        
        # 检查内容长度
        if len(content) > self.MAX_CONTENT_LENGTH:
            issues.append(SecurityIssue(
                severity='high',
                category='excessive_length',
                description=f'内容过长（{len(content)} > {self.MAX_CONTENT_LENGTH}字符），可能导致性能问题',
                matched_pattern='',
                position=0
            ))
        
        # 检查每行长度
        for i, line in enumerate(content.split('\n')):
            if len(line) > self.MAX_LINE_LENGTH:
                issues.append(SecurityIssue(
                    severity='medium',
                    category='excessive_length',
                    description=f'第{i+1}行过长（{len(line)} > {self.MAX_LINE_LENGTH}字符）',
                    matched_pattern=line[:50] + '...',
                    position=i
                ))
        
        # SQL注入检测
        sql_issues = self._detect_patterns(
            content, 
            self.SQL_INJECTION_PATTERNS, 
            'sql_injection',
            'critical',
            '检测到潜在的SQL注入模式'
        )
        issues.extend(sql_issues)
        
        # 命令注入检测
        cmd_issues = self._detect_patterns(
            content,
            self.COMMAND_INJECTION_PATTERNS,
            'command_injection',
            'critical',
            '检测到潜在的命令注入模式'
        )
        issues.extend(cmd_issues)
        
        # Prompt注入检测
        prompt_issues = self._detect_patterns(
            content,
            self.PROMPT_INJECTION_PATTERNS,
            'prompt_injection',
            'high',
            '检测到潜在的Prompt注入攻击'
        )
        issues.extend(prompt_issues)
        
        # XSS检测
        xss_issues = self._detect_patterns(
            content,
            self.XSS_PATTERNS,
            'xss',
            'high',
            '检测到潜在的XSS脚本'
        )
        issues.extend(xss_issues)
        
        # 恶意URL检测
        url_issues = self._detect_patterns(
            content,
            self.MALICIOUS_URL_PATTERNS,
            'malicious_url',
            'medium',
            '检测到可疑URL'
        )
        issues.extend(url_issues)
        
        # 敏感关键词检测
        for keyword in self.SENSITIVE_KEYWORDS:
            if keyword.lower() in content.lower():
                warnings.append(f'包含敏感关键词: {keyword}')
        
        # 计算安全分数
        security_score = self._calculate_security_score(issues)
        
        # 判断是否安全
        is_safe = self._is_safe(issues, security_score)
        
        return ScanResult(
            is_safe=is_safe,
            security_score=security_score,
            issues=issues,
            warnings=warnings
        )
    
    def _detect_patterns(
        self, 
        content: str, 
        patterns: List[str], 
        category: str,
        severity: str,
        description_template: str
    ) -> List[SecurityIssue]:
        """
        检测内容中的模式匹配
        
        Args:
            content: 待检测内容
            patterns: 正则表达式模式列表
            category: 问题类别
            severity: 严重程度
            description_template: 描述模板
        
        Returns:
            List[SecurityIssue]: 发现的问题列表
        """
        issues = []
        
        for pattern in patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                issues.append(SecurityIssue(
                    severity=severity,
                    category=category,
                    description=f'{description_template}: {match.group(0)[:50]}',
                    matched_pattern=match.group(0),
                    position=match.start()
                ))
        
        return issues
    
    def _calculate_security_score(self, issues: List[SecurityIssue]) -> float:
        """
        计算安全分数（0-100）
        
        Args:
            issues: 问题列表
        
        Returns:
            float: 安全分数
        """
        if not issues:
            return 100.0
        
        # 扣分总和
        total_deduction = sum(self.SEVERITY_SCORES[issue.severity] for issue in issues)
        
        # 计算分数（最低0分）
        score = max(0.0, 100.0 - total_deduction)
        
        return round(score, 2)
    
    def _is_safe(self, issues: List[SecurityIssue], security_score: float) -> bool:
        """
        判断内容是否安全
        
        Args:
            issues: 问题列表
            security_score: 安全分数
        
        Returns:
            bool: 是否安全
        """
        # 有critical问题直接判定为不安全
        critical_issues = [i for i in issues if i.severity == 'critical']
        if critical_issues:
            return False
        
        # 有2个或以上high问题判定为不安全
        high_issues = [i for i in issues if i.severity == 'high']
        if len(high_issues) >= 2:
            return False
        
        # 严格模式下，有high问题也判定为不安全
        if self.strict_mode and high_issues:
            return False
        
        # 安全分数低于70分判定为不安全
        if security_score < 70.0:
            return False
        
        return True
    
    def get_sanitized_content(self, content: str) -> Tuple[str, List[str]]:
        """
        清理内容中的不安全部分（尽力而为，不保证100%安全）
        
        Args:
            content: 原始内容
        
        Returns:
            Tuple[str, List[str]]: (清理后的内容, 清理操作列表)
        """
        sanitized = content
        operations = []
        
        # 移除HTML脚本标签
        script_pattern = r'<script[^>]*>.*?</script>'
        if re.search(script_pattern, sanitized, re.IGNORECASE | re.DOTALL):
            sanitized = re.sub(script_pattern, '', sanitized, flags=re.IGNORECASE | re.DOTALL)
            operations.append('移除了<script>标签')
        
        # 移除iframe/embed/object标签
        unsafe_tags = ['iframe', 'embed', 'object']
        for tag in unsafe_tags:
            tag_pattern = f'<{tag}[^>]*>.*?</{tag}>'
            if re.search(tag_pattern, sanitized, re.IGNORECASE | re.DOTALL):
                sanitized = re.sub(tag_pattern, '', sanitized, flags=re.IGNORECASE | re.DOTALL)
                operations.append(f'移除了<{tag}>标签')
        
        # 移除javascript:协议
        if 'javascript:' in sanitized.lower():
            sanitized = re.sub(r'javascript:', '', sanitized, flags=re.IGNORECASE)
            operations.append('移除了javascript:协议')
        
        # 移除事件处理器属性
        event_pattern = r'on\w+\s*=\s*["\'][^"\']*["\']'
        if re.search(event_pattern, sanitized, re.IGNORECASE):
            sanitized = re.sub(event_pattern, '', sanitized, flags=re.IGNORECASE)
            operations.append('移除了事件处理器属性')
        
        return sanitized, operations


def scan_skill_content(content: str, strict_mode: bool = False) -> ScanResult:
    """
    便捷函数：扫描技能内容
    
    Args:
        content: 技能内容
        strict_mode: 是否使用严格模式
    
    Returns:
        ScanResult: 扫描结果
    """
    scanner = SkillSecurityScanner(strict_mode=strict_mode)
    return scanner.scan_content(content)


def is_skill_safe(content: str, strict_mode: bool = False) -> bool:
    """
    便捷函数：检查技能内容是否安全
    
    Args:
        content: 技能内容
        strict_mode: 是否使用严格模式
    
    Returns:
        bool: 是否安全
    """
    result = scan_skill_content(content, strict_mode)
    return result.is_safe
