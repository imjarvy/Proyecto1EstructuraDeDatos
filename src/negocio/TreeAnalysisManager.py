"""
TreeAnalysisManager for tree audit, depth penalties, and profitability analysis.
"""


class TreeAnalysisManager:
    """Encapsulates analysis and pricing-related tree operations."""

    def apply_depth_penalties(self, node, depth: int, limit: int) -> None:
        """
        Apply critical-depth pricing rule recursively.

        Nodes deeper than limit receive a 25% surcharge over base_price.
        Nodes at or above the limit are reset to base_price.
        """
        if node is None:
            return

        if depth > limit:
            node.final_price = round(node.base_price * 1.25, 2)
        else:
            node.final_price = node.base_price

        self.apply_depth_penalties(node.left, depth + 1, limit)
        self.apply_depth_penalties(node.right, depth + 1, limit)

    def audit_node(self, node, report: list, depth: int = 0) -> bool:
        """
        Verify AVL invariants recursively.

        Checks:
            - balance_factor in {-1, 0, 1}
            - stored height equals computed height
        """
        if node is None:
            return True

        issues = []

        if node.balance_factor not in (-1, 0, 1):
            issues.append(
                f"Balance factor = {node.balance_factor}, expected value in {{-1, 0, 1}}"
            )

        def _h(current):
            return current.height if current else -1

        expected_height = max(_h(node.left), _h(node.right)) + 1 if (node.left or node.right) else 0
        if node.height != expected_height:
            issues.append(
                f"Stored height = {node.height}, but computed height = {expected_height}"
            )

        if issues:
            report.append({"flight_code": node.flight_code, "depth": depth, "issues": issues})

        left_ok = self.audit_node(node.left, report, depth + 1)
        right_ok = self.audit_node(node.right, report, depth + 1)
        return len(issues) == 0 and left_ok and right_ok

    @staticmethod
    def profitability(node) -> float:
        """
        Compute node profitability.

        Promotion is already reflected in final_price by the manager.
        """
        return node.passengers * node.final_price

    def find_least_profitable(self, node, depth: int = 0):
        """
        Find node with lowest profitability.

        Tie-breakers:
            1. Greater depth first.
            2. Larger flight_code (lexicographic) if depth ties.
        """
        if node is None:
            return None

        best_node = None
        best_depth = -1
        stack = [(node, depth)]

        while stack:
            current, current_depth = stack.pop()
            if current is None:
                continue

            if best_node is None:
                best_node, best_depth = current, current_depth
            else:
                current_profit = self.profitability(current)
                best_profit = self.profitability(best_node)
                if (
                    current_profit < best_profit
                    or (current_profit == best_profit and current_depth > best_depth)
                    or (
                        current_profit == best_profit
                        and current_depth == best_depth
                        and current.flight_code > best_node.flight_code
                    )
                ):
                    best_node, best_depth = current, current_depth

            stack.append((current.left, current_depth + 1))
            stack.append((current.right, current_depth + 1))

        return best_node
