"""
AST to LookML Converter - Converts Tableau formula AST to LookML SQL expressions.

This module handles the conversion of parsed Tableau formula ASTs into valid LookML SQL syntax.
The converter uses the Visitor pattern to recursively walk the AST tree and build LookML expressions.
"""

import logging
from typing import Dict
from ..models.ast_schema import ASTNode, NodeType, DataType

logger = logging.getLogger(__name__)


class ASTToLookMLConverter:
    """
    Converts Tableau formula AST nodes to LookML SQL expressions.

    Key Design Principles:
    1. Recursive tree traversal using the Visitor pattern
    2. Each node type has a specific conversion method
    3. Simple string building - no complex logic
    4. Function registry for Tableau → LookML function mapping
    """

    def __init__(self):
        """Initialize the converter with function mappings."""
        self.function_registry = self._build_function_registry()
        logger.debug("AST to LookML converter initialized")

    def convert_to_lookml(self, ast_node: ASTNode, table_context: str = "TABLE") -> str:
        """
        Convert an AST node to LookML SQL expression.

        Args:
            ast_node: Root AST node to convert
            table_context: Table context for field references (default: "TABLE")

        Returns:
            str: LookML SQL expression

        Example:
            Input AST: FieldRef(field_name="adult")
            Output: "${TABLE}.adult"
        """
        try:
            result = self._convert_node(ast_node, table_context)
            logger.debug(f"Converted AST to LookML: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to convert AST to LookML: {str(e)}")
            return f"/* Conversion error: {str(e)} */"

    def _convert_node(self, node: ASTNode, table_context: str) -> str:
        """
        Core recursive method that converts individual AST nodes.

        This is the heart of the converter - it dispatches to specific
        conversion methods based on the node type.
        """
        if node is None:
            return "NULL"

        # Dispatch to specific conversion methods based on node type
        # This is the Visitor pattern in action
        if node.node_type == NodeType.FIELD_REF:
            return self._convert_field_reference(node, table_context)
        elif node.node_type == NodeType.LITERAL:
            return self._convert_literal(node)
        elif node.node_type == NodeType.ARITHMETIC:
            return self._convert_arithmetic(node, table_context)
        elif node.node_type == NodeType.COMPARISON:
            return self._convert_comparison(node, table_context)
        elif node.node_type == NodeType.LOGICAL:
            return self._convert_logical(node, table_context)
        elif node.node_type == NodeType.FUNCTION:
            return self._convert_function(node, table_context)
        elif node.node_type == NodeType.CONDITIONAL:
            return self._convert_conditional(node, table_context)
        elif node.node_type == NodeType.CASE:
            return self._convert_case(node, table_context)
        elif node.node_type == NodeType.UNARY:
            return self._convert_unary(node, table_context)
        else:
            logger.warning(f"Unsupported node type: {node.node_type}")
            return f"/* Unsupported: {node.node_type} */"

    def _build_function_registry(self) -> Dict[str, str]:
        """
        Build the function mapping registry.

        This maps Tableau function names to their LookML equivalents.
        Most are direct mappings, but some require transformation.
        """
        return {
            # Aggregation functions - direct mapping
            "SUM": "SUM",
            "COUNT": "COUNT",
            "AVG": "AVG",
            "MIN": "MIN",
            "MAX": "MAX",
            "MEDIAN": "MEDIAN",
            # String functions - mostly direct
            "UPPER": "UPPER",
            "LOWER": "LOWER",
            "LEN": "LENGTH",  # Tableau LEN → SQL LENGTH
            "TRIM": "TRIM",
            "LEFT": "LEFT",
            "RIGHT": "RIGHT",
            "MID": "SUBSTR",  # Tableau MID → SQL SUBSTR
            # Math functions - direct mapping
            "ABS": "ABS",
            "ROUND": "ROUND",
            "CEILING": "CEIL",  # Tableau CEILING → SQL CEIL
            "FLOOR": "FLOOR",
            "SQRT": "SQRT",
            "POWER": "POWER",
            # Date functions - more complex, handled specially
            "YEAR": "EXTRACT(YEAR FROM {})",
            "MONTH": "EXTRACT(MONTH FROM {})",
            "DAY": "EXTRACT(DAY FROM {})",
            "NOW": "CURRENT_TIMESTAMP",
            "TODAY": "CURRENT_DATE",
        }

    # CONVERSION METHODS - Each handles a specific AST node type

    def _convert_field_reference(self, node: ASTNode, table_context: str) -> str:
        """
        Convert field reference: [field_name] → ${TABLE}.field_name

        This is the SIMPLEST conversion - just wrap field name in LookML syntax.

        Args:
            node: FieldRef AST node with field_name attribute
            table_context: Table context (usually "TABLE")

        Returns:
            LookML field reference

        Examples:
            [adult] → ${TABLE}.adult
            [budget] → ${TABLE}.budget
            [Movie Title] → ${TABLE}.movie_title (spaces converted to underscores)
        """
        if not node.field_name:
            logger.warning("Field reference node missing field_name")
            return "/* Missing field name */"

        # Clean field name - replace spaces with underscores, make lowercase
        clean_field_name = node.field_name.lower().replace(" ", "_")

        # Build LookML field reference
        lookml_ref = f"${{{table_context}}}.{clean_field_name}"

        logger.debug(f"Converted field reference: {node.field_name} → {lookml_ref}")
        return lookml_ref

    def _convert_literal(self, node: ASTNode) -> str:
        """
        Convert literal values: strings, numbers, booleans, null.

        This handles constants in formulas like "Adult", 123, TRUE, NULL.

        Examples:
            "Hello" → 'Hello'  (wrap strings in quotes)
            123 → 123          (numbers as-is)
            TRUE → TRUE        (booleans as-is)
            NULL → NULL        (null as-is)
        """
        if node.value is None:
            return "NULL"

        # Handle different data types
        if node.data_type == DataType.STRING:
            # Escape single quotes and wrap in quotes
            escaped_value = str(node.value).replace("'", "\\'")
            return f"'{escaped_value}'"

        elif node.data_type == DataType.BOOLEAN:
            # Convert Python boolean to SQL boolean
            return "TRUE" if node.value else "FALSE"

        elif node.data_type in [DataType.INTEGER, DataType.REAL]:
            # Numbers can be used directly
            return str(node.value)

        else:
            # Default: treat as string
            escaped_value = str(node.value).replace("'", "\\'")
            return f"'{escaped_value}'"

    def _convert_arithmetic(self, node: ASTNode, table_context: str) -> str:
        """
        Convert arithmetic operations: +, -, *, /, %, ^

        This is where RECURSION happens! We convert the left and right
        child nodes, then combine them with the operator.

        Args:
            node: Arithmetic AST node with operator, left, right
            table_context: Table context for child nodes

        Returns:
            LookML arithmetic expression

        Examples:
            [budget] + [revenue] → (${TABLE}.budget + ${TABLE}.revenue)
            [popularity] * 2     → (${TABLE}.popularity * 2)
            [budget] / [runtime] → (${TABLE}.budget / ${TABLE}.runtime)
        """
        if not node.left or not node.right:
            logger.warning("Arithmetic node missing left or right operand")
            return "/* Missing operand */"

        # RECURSION: Convert left and right child nodes
        left_expr = self._convert_node(node.left, table_context)
        right_expr = self._convert_node(node.right, table_context)

        # Handle special operators
        operator = node.operator
        if operator == "^":
            # Tableau uses ^ for power, SQL uses POWER function
            return f"POWER({left_expr}, {right_expr})"
        elif operator == "%":
            # Modulo operator
            return f"MOD({left_expr}, {right_expr})"
        else:
            # Standard operators: +, -, *, /
            # Wrap in parentheses to preserve precedence
            return f"({left_expr} {operator} {right_expr})"

    def _convert_comparison(self, node: ASTNode, table_context: str) -> str:
        """
        Convert comparison operations: =, !=, <, >, <=, >=

        Similar to arithmetic, but for comparison operators.

        Examples:
            [adult] = TRUE        → (${TABLE}.adult = TRUE)
            [budget] > 1000000    → (${TABLE}.budget > 1000000)
            [rating] <= 5.0       → (${TABLE}.rating <= 5.0)
        """
        if not node.left or not node.right:
            logger.warning("Comparison node missing left or right operand")
            return "/* Missing operand */"

        # RECURSION: Convert both sides
        left_expr = self._convert_node(node.left, table_context)
        right_expr = self._convert_node(node.right, table_context)

        # Handle special comparison operators
        operator = node.operator
        if operator == "<>" or operator == "!=":
            # Both Tableau <> and != map to SQL !=
            operator = "!="

        return f"({left_expr} {operator} {right_expr})"

    def _convert_logical(self, node: ASTNode, table_context: str) -> str:
        """
        Convert logical operations: AND, OR

        Examples:
            [adult] AND [rated_r] → (${TABLE}.adult AND ${TABLE}.rated_r)
            [budget] > 1000 OR [revenue] > 5000 → (...complex expression...)
        """
        if not node.left or not node.right:
            logger.warning("Logical node missing left or right operand")
            return "/* Missing operand */"

        # RECURSION: Convert both sides
        left_expr = self._convert_node(node.left, table_context)
        right_expr = self._convert_node(node.right, table_context)

        operator = node.operator.upper()  # Ensure uppercase AND, OR
        return f"({left_expr} {operator} {right_expr})"

    def _convert_unary(self, node: ASTNode, table_context: str) -> str:
        """
        Convert unary operations: NOT, - (negative)

        Examples:
            NOT [adult]  → NOT ${TABLE}.adult
            -[budget]    → -${TABLE}.budget
        """
        if not node.operand:
            logger.warning("Unary node missing operand")
            return "/* Missing operand */"

        # RECURSION: Convert the operand
        operand_expr = self._convert_node(node.operand, table_context)

        operator = node.operator.upper() if node.operator else ""

        if operator == "NOT":
            return f"NOT {operand_expr}"
        elif operator == "-":
            return f"-{operand_expr}"
        else:
            return f"{operator}{operand_expr}"

    def _convert_function(self, node: ASTNode, table_context: str) -> str:
        """
        Convert function calls using the function registry.

        This is the SMART part - we map Tableau functions to LookML equivalents.

        Args:
            node: Function AST node with function_name and arguments
            table_context: Table context for arguments

        Returns:
            LookML function call

        Examples:
            UPPER([title]) → UPPER(${TABLE}.title)
            SUM([budget])  → SUM(${TABLE}.budget)
            LEN([title])   → LENGTH(${TABLE}.title)    # Function name mapping!
        """
        if not node.function_name:
            logger.warning("Function node missing function_name")
            return "/* Missing function name */"

        function_name = node.function_name.upper()

        # Convert all arguments recursively
        converted_args = []
        for arg in node.arguments:
            arg_expr = self._convert_node(arg, table_context)
            converted_args.append(arg_expr)

        # Look up function in registry
        if function_name in self.function_registry:
            lookml_function = self.function_registry[function_name]

            # Handle special function formats
            if "{}" in lookml_function:
                # Special format like EXTRACT(YEAR FROM {})
                if len(converted_args) == 1:
                    return lookml_function.format(converted_args[0])
                else:
                    logger.warning(
                        f"Special function {function_name} expects 1 argument, got {len(converted_args)}"
                    )
                    return f"/* {function_name}: wrong argument count */"
            else:
                # Standard function format: FUNCTION(arg1, arg2, ...)
                args_str = ", ".join(converted_args)
                return f"{lookml_function}({args_str})"
        else:
            # Function not in registry - use as-is with warning
            logger.warning(f"Unknown function: {function_name}")
            args_str = ", ".join(converted_args)
            return f"{function_name}({args_str})"

    def _convert_conditional(self, node: ASTNode, table_context: str) -> str:
        """
        Convert IF-THEN-ELSE to CASE-WHEN-ELSE.

        This is the MOST COMPLEX conversion because Tableau and LookML
        use different syntax for conditionals.

        Args:
            node: Conditional AST node with condition, then_branch, else_branch
            table_context: Table context for expressions

        Returns:
            LookML CASE expression

        Examples:
            IF [adult] THEN "Adult" ELSE "Child" END
            ↓
            CASE WHEN ${TABLE}.adult THEN 'Adult' ELSE 'Child' END

            IF [budget] > 1000000 THEN "Blockbuster" ELSE "Independent" END
            ↓
            CASE WHEN (${TABLE}.budget > 1000000) THEN 'Blockbuster' ELSE 'Independent' END
        """
        if not node.condition or not node.then_branch:
            logger.warning("Conditional node missing condition or then_branch")
            return "/* Incomplete conditional */"

        # Convert each part recursively
        condition_expr = self._convert_node(node.condition, table_context)
        then_expr = self._convert_node(node.then_branch, table_context)

        # Handle optional ELSE clause
        if node.else_branch:
            else_expr = self._convert_node(node.else_branch, table_context)
        else:
            else_expr = "NULL"

        # Build CASE expression
        case_expr = f"CASE WHEN {condition_expr} THEN {then_expr} ELSE {else_expr} END"

        logger.debug(f"Converted conditional to: {case_expr}")
        return case_expr

    def _convert_case(self, node: ASTNode, table_context: str) -> str:
        """
        Convert CASE-WHEN-ELSE to LookML CASE expression.

        Tableau CASE statements can be:
        1. Simple CASE: CASE [field] WHEN value1 THEN result1 WHEN value2 THEN result2 ELSE default END
        2. Searched CASE: CASE WHEN condition1 THEN result1 WHEN condition2 THEN result2 ELSE default END

        Args:
            node: CASE AST node with case_expression, when_clauses, else_branch
            table_context: Table context for expressions

        Returns:
            LookML CASE expression

        Examples:
            CASE [category] WHEN "Electronics" THEN 0.1 WHEN "Books" THEN 0.05 ELSE 0 END
            ↓
            CASE ${TABLE}.category WHEN 'Electronics' THEN 0.1 WHEN 'Books' THEN 0.05 ELSE 0 END

            CASE WHEN [sales] > 1000 THEN "High" WHEN [sales] > 500 THEN "Medium" ELSE "Low" END
            ↓
            CASE WHEN (${TABLE}.sales > 1000) THEN 'High' WHEN (${TABLE}.sales > 500) THEN 'Medium' ELSE 'Low' END
        """
        if not node.when_clauses:
            logger.warning("CASE node missing when_clauses")
            return "/* CASE statement with no WHEN clauses */"

        case_parts = ["CASE"]

        # Handle simple CASE vs searched CASE
        if node.case_expression:
            # Simple CASE: CASE [field] WHEN value1 THEN result1 ...
            case_expr = self._convert_node(node.case_expression, table_context)
            case_parts.append(case_expr)
        # If no case_expression, it's searched CASE: CASE WHEN condition1 THEN result1 ...

        # Convert all WHEN clauses
        for when_clause in node.when_clauses:
            condition_expr = self._convert_node(when_clause.condition, table_context)
            result_expr = self._convert_node(when_clause.result, table_context)

            case_parts.append(f"WHEN {condition_expr} THEN {result_expr}")

        # Handle optional ELSE clause
        if node.else_branch:
            else_expr = self._convert_node(node.else_branch, table_context)
            case_parts.append(f"ELSE {else_expr}")

        case_parts.append("END")

        # Build final CASE expression
        case_expr = " ".join(case_parts)

        logger.debug(f"Converted CASE statement to: {case_expr}")
        return case_expr
