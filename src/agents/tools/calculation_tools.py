"""
Calculation tools for financial computations.
"""
from typing import Optional, List, Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


class CalculationInput(BaseModel):
    """Input for calculation tool."""
    calculation_type: str = Field(
        description="Type of calculation: 'outperformance', 'attribution', 'weight_change', 'custom'"
    )
    values: List[float] = Field(description="List of numeric values to use in calculation")
    labels: Optional[List[str]] = Field(default=None, description="Optional labels for the values")


class FinancialCalculationTool(BaseTool):
    """Tool for financial calculations."""
    
    name: str = "calculate_metrics"
    description: str = """Perform financial calculations.
    Supported calculations:
    - outperformance: Calculate fund return minus benchmark return
    - attribution: Calculate contribution attribution
    - weight_change: Calculate weight changes between periods
    - custom: Perform custom arithmetic
    
    Provide the calculation type and the numeric values."""
    args_schema: Type[BaseModel] = CalculationInput
    
    def _run(
        self, 
        calculation_type: str, 
        values: List[float],
        labels: Optional[List[str]] = None
    ) -> str:
        """Perform calculation."""
        try:
            if calculation_type == "outperformance":
                if len(values) < 2:
                    return "Need at least 2 values: fund_return and benchmark_return"
                
                fund_return = values[0]
                benchmark_return = values[1]
                outperformance = fund_return - benchmark_return
                
                return f"""Outperformance Calculation:
Fund Return: {fund_return:+.2f}%
Benchmark Return: {benchmark_return:+.2f}%
Outperformance: {outperformance:+.2f}%
{"(Fund outperformed)" if outperformance > 0 else "(Fund underperformed)"}"""
            
            elif calculation_type == "attribution":
                if not labels or len(labels) != len(values):
                    labels = [f"Item {i+1}" for i in range(len(values))]
                
                total = sum(values)
                result_lines = ["Attribution Analysis:"]
                
                for label, value in zip(labels, values):
                    pct = (value / total * 100) if total != 0 else 0
                    result_lines.append(f"  {label}: {value:+.2f}% ({pct:.1f}% of total)")
                
                result_lines.append(f"\nTotal: {total:+.2f}%")
                return "\n".join(result_lines)
            
            elif calculation_type == "weight_change":
                if len(values) < 2:
                    return "Need at least 2 values: old_weight and new_weight"
                
                old_weight = values[0]
                new_weight = values[1]
                change = new_weight - old_weight
                pct_change = ((new_weight - old_weight) / old_weight * 100) if old_weight != 0 else 0
                
                label = labels[0] if labels else "Position"
                
                return f"""Weight Change for {label}:
Previous Weight: {old_weight:.2f}%
Current Weight: {new_weight:.2f}%
Absolute Change: {change:+.2f}%
Relative Change: {pct_change:+.1f}%"""
            
            elif calculation_type == "custom":
                # Basic statistics
                total = sum(values)
                avg = total / len(values) if values else 0
                min_val = min(values) if values else 0
                max_val = max(values) if values else 0
                
                return f"""Custom Calculation:
Values: {', '.join(f'{v:.2f}' for v in values)}
Sum: {total:.2f}
Average: {avg:.2f}
Min: {min_val:.2f}
Max: {max_val:.2f}
Count: {len(values)}"""
            
            else:
                return f"Unknown calculation type: {calculation_type}"
                
        except Exception as e:
            return f"Calculation error: {str(e)}"
    
    async def _arun(
        self, 
        calculation_type: str, 
        values: List[float],
        labels: Optional[List[str]] = None
    ) -> str:
        """Async execution."""
        return self._run(calculation_type, values, labels)


class ExtractNumbersInput(BaseModel):
    """Input for number extraction tool."""
    text: str = Field(description="Text containing numbers to extract")
    number_type: str = Field(
        default="percentage",
        description="Type of numbers to extract: 'percentage', 'currency', 'all'"
    )


class ExtractNumbersTool(BaseTool):
    """Tool for extracting numbers from text."""
    
    name: str = "extract_numbers"
    description: str = """Extract numeric values from text.
    Use this to pull out specific numbers like percentages, currency amounts,
    or other numeric data from document text for calculations."""
    args_schema: Type[BaseModel] = ExtractNumbersInput
    
    def _run(self, text: str, number_type: str = "percentage") -> str:
        """Extract numbers from text."""
        import re
        
        numbers = []
        
        if number_type in ["percentage", "all"]:
            # Find percentages
            pct_pattern = r'([\-\+]?\d+\.?\d*)\s*%'
            matches = re.findall(pct_pattern, text)
            for match in matches:
                try:
                    numbers.append({
                        "value": float(match),
                        "type": "percentage",
                        "original": f"{match}%"
                    })
                except:
                    pass
        
        if number_type in ["currency", "all"]:
            # Find currency values
            currency_pattern = r'[\$\€\£\¥]?\s*([\d,]+\.?\d*)\s*(million|billion|M|B|mn|bn)?'
            matches = re.findall(currency_pattern, text)
            for match in matches:
                try:
                    value = float(match[0].replace(",", ""))
                    multiplier = match[1].lower() if match[1] else ""
                    if multiplier in ["million", "m", "mn"]:
                        value *= 1_000_000
                    elif multiplier in ["billion", "b", "bn"]:
                        value *= 1_000_000_000
                    
                    numbers.append({
                        "value": value,
                        "type": "currency",
                        "original": f"{match[0]} {match[1]}".strip()
                    })
                except:
                    pass
        
        if not numbers:
            return "No numbers found in the text."
        
        # Format output
        result_lines = [f"Found {len(numbers)} number(s):"]
        for num in numbers[:20]:  # Limit output
            result_lines.append(f"  {num['original']} = {num['value']} ({num['type']})")
        
        return "\n".join(result_lines)
    
    async def _arun(self, text: str, number_type: str = "percentage") -> str:
        """Async execution."""
        return self._run(text, number_type)


def create_calculation_tool() -> FinancialCalculationTool:
    """Create a financial calculation tool."""
    return FinancialCalculationTool()


def create_extract_numbers_tool() -> ExtractNumbersTool:
    """Create a number extraction tool."""
    return ExtractNumbersTool()
