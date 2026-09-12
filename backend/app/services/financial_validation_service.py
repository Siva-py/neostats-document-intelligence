from typing import Any
import re

TOLERANCE = 1.0

def _to_number(value):
    if value is None:
        return None

    if isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()

    if not text:
        return None

    # Handle accounting-style negative values: (123.45)
    is_negative = (
        text.startswith("(")
        and text.endswith(")")
    )

    if is_negative:
        text = text[1:-1].strip()

    # Remove currency symbols, spaces and other non-numeric
    # characters while keeping decimal separators and minus sign.
    cleaned = "".join(
        char
        for char in text
        if char.isdigit() or char in ".,-"
    )

    if not cleaned:
        return None

    # If both separators exist, the LAST separator is treated
    # as the decimal separator.
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "")
            cleaned = cleaned.replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")

    # Only comma exists.
    elif "," in cleaned:
        parts = cleaned.split(",")

        # One or two digits after comma -> decimal comma.
        if len(parts) == 2 and len(parts[1]) <= 2:
            cleaned = cleaned.replace(",", ".")

        # Three digits after comma -> thousands separator.
        else:
            cleaned = cleaned.replace(",", "")

    # Only dot exists -> normal decimal notation.
    else:
        pass

    try:
        number = float(cleaned)

        if is_negative:
            number = -abs(number)

        return number

    except ValueError:
        return None

    
def _result(
    check_name: str,
    formula: str,
    inputs: dict[str, Any],
    calculated: float | None,
    reported: float | None,
    variance: float | None,
    status: str,
) -> dict[str, Any]:
    return {
        "check": check_name,
        "formula": formula,
        "inputs": inputs,
        "calculated": calculated,
        "reported": reported,
        "variance": variance,
        "status": status,
    }


def _compare(
    check_name: str,
    formula: str,
    inputs: dict[str, Any],
    calculated: Any,
    reported: Any,
) -> dict[str, Any]:

    calculated_number = _to_number(calculated)
    reported_number = _to_number(reported)

    if calculated_number is None or reported_number is None:
        return _result(
            check_name=check_name,
            formula=formula,
            inputs=inputs,
            calculated=calculated_number,
            reported=reported_number,
            variance=None,
            status="NOT_APPLICABLE",
        )

    variance = calculated_number - reported_number

    status = (
        "PASS"
        if abs(variance) <= TOLERANCE
        else "FAIL"
    )

    return _result(
        check_name=check_name,
        formula=formula,
        inputs=inputs,
        calculated=calculated_number,
        reported=reported_number,
        variance=variance,
        status=status,
    )


def validate_document(
    document_type: str,
    extracted_data: dict[str, Any],
) -> dict[str, Any]:

    if document_type == "invoice":
        return validate_invoice(extracted_data)

    if document_type == "balance_sheet":
        return validate_balance_sheet(extracted_data)

    if document_type == "profit_and_loss":
        return validate_profit_and_loss(extracted_data)

    if document_type == "cash_flow_statement":
        return validate_cash_flow(extracted_data)

    return {
        "status": "FAILED",
        "checks": [],
        "error": f"Unsupported document type: {document_type}",
    }


def validate_invoice(extracted_data):
    """
    Validate extracted invoice financial relationships.

    Checks:
    1. Quantity × Unit Price ≈ Line Total
    2. Sum of Line Totals ≈ Subtotal / Taxable Amount
    3. Taxable Amount + Tax ≈ Total
    4. Cash Paid - Total ≈ Change

    Missing information results in NOT_APPLICABLE.
    No values are inferred or modified.
    """

    results = []

    sections = extracted_data.get("financial_statement", {}).get(
        "sections", []
    )

    def normalize_key(value):
        key = str(value).lower()
        key = re.sub(r"[^a-z0-9]+", "", key)

        # Remove currency suffixes such as _eur, _usd, _inr, etc.
        key = re.sub(
            r"(eur|usd|inr|gbp|aed|sar|cad|aud|sgd|jpy|rm)$",
            "",
            key,
        )

        return key


    def find_value(values, aliases):
        """
        Find a value using flexible field-name aliases.
        Matching is case-insensitive, ignores spaces/underscores,
        and supports currency-suffixed fields such as total_eur.
        """
        if not isinstance(values, dict):
            return None

        normalized = {
            normalize_key(key): value
            for key, value in values.items()
        }

        for alias in aliases:
            key = normalize_key(alias)

            if key in normalized:
                return normalized[key]

        return None

    # ---------------------------------------------------------
    # Collect invoice line items and summary values
    # ---------------------------------------------------------

    line_items = []
    summary_values = {}

    summary_aliases = {
        "subtotal": [
            "subtotal",
            "sub_total",
            "sub total",
            "s. total",
            "s.total",
            "stotal",
            "net_total",
            "net total",
            "net_amount",
            "net amount",
        ],

        "taxable_amount": [
            "taxable_amount",
            "taxable amount",
            "taxable_value",
            "taxable value",
            "taxable",
            "total_excluding_gst",
            "total excluding gst",
            "total (excluding gst)",
            "total_excluding_tax",
            "total excluding tax",
            "total (excluding tax)",
            "net_worth",
            "net worth",
        ],

        "tax": [
            "tax",
            "tax_amount",
            "tax amount",
            "tax(rm)",
            "tax(rm)",
            "tax rm",   
            "gst",
            "gst_amount",
            "gst amount",
            "gst_payable",
            "gst payable",
            "vat",
            "vat_amount",
            "vat amount",
            "sales_tax",
            "sales tax",
            "hst",
            "hst amount",
        ],

        "total": [
            "total",
            "grand_total",
            "grand total",
            "total_due",
            "total due",
            "amount_due",
            "amount due",
            "gross_total",
            "gross total",
            "total_amount",
            "total amount",
            "total_inclusive_gst",
            "total inclusive gst",
            "total incl gst",
            "total incl. gst",
            "total_inclusive_of_gst",
            "total inclusive of gst",
            "total (inclusive of gst)",
            "total_inclusive_tax",
            "total inclusive of tax",
            "total sales inclusive gst",
            "total sales (inclusive gst)",
        ],
        "discount": [
            "discount",
            "discount amount",
            "discount_amount",
            "discount value",
            "discount_value",
        ],
        "round_off": [
            "round off",
            "round_off",
            "rounding",
            "rounding off",
            "rounding adjustment",
        ],

        "cash_paid": [
            "cash",
            "cash_paid",
            "cash paid",
            "paid",
            "amount_paid",
            "amount paid",
            "customer_payment",
            "customer payment",
            "customer's payment",
            "payment",
        ],

        "change": [
            "change",
            "change_amount",
            "change amount",
            "cash change",
        ],
    }

    for section in sections:

        section_name = str(
            section.get("section_name", "")
        ).lower()

        for item in section.get("line_items", []):

            if not isinstance(item, dict):
                continue

            label = str(
                item.get("line_item", "")
            ).strip()

            values = item.get("values", {})

            if not isinstance(values, dict):
                values = {}

            # -------------------------------------------------
            # Identify actual product/service line items
            # -------------------------------------------------

            quantity = find_value(
                values,
                [
                    "quantity",
                    "qty",
                    "quant",
                ],
            )

            unit_price = find_value(
                values,
                [
                    "unit_price",
                    "unitprice",
                    "u.price",
                    "uprice",
                    "unit price",
                    "unit rate",
                    "price",
                    "rate",
                    "rate_per_pcs",
                    "rate per pcs",
                    "rate_per_piece",
                    "rate per piece",
                    "price_per_pcs",
                    "price per pcs",
                    "net_price",
                ],
            )

            line_total = find_value(
            values,
            [
                "line_total",
                "linetotal",
                "net worth",
                "net amount",
                "total",
                "total_amount",
                "total amount",
                "amount",
                "extension",
                "extension_amount",
                "gross_worth",
            ],
        )

            # Only treat rows containing a quantity AND a unit price
            # as actual invoice line items.
            #
            # Summary rows such as Sub Total, GST, Round Off and Total
            # must not participate in the line-item calculation.

            if (
                quantity is not None
                and unit_price is not None
                and line_total is not None
            ):
                line_items.append(
                    {
                        "label": label,
                        "quantity": quantity,
                        "unit_price": unit_price,
                        "line_total": line_total,
                        "discount_percent": find_value(
                            values,
                            [
                                "discount_percent",
                                "discount",
                                "disc_percent",
                                "discount_rate",
                            ],
                        ),
                    }
                )

            # -------------------------------------------------
            # Collect summary-level financial values
            # -------------------------------------------------

            tax_component_values = []
            explicit_total_tax = None

            for section in sections:

                for item in section.get("line_items", []):

                    if not isinstance(item, dict):
                        continue

                    label = str(
                        item.get("line_item", "")
                    ).strip()

                    values = item.get("values", {})

                    if not isinstance(values, dict):
                        values = {}

                    # -------------------------------------------------
                    # Collect normal summary-level values
                    # -------------------------------------------------

                    for field_name, aliases in summary_aliases.items():

                        # Tax is handled separately below.
                        if field_name == "tax":
                            continue

                        safe_aliases = [
                            alias
                            for alias in aliases
                            if alias.lower() not in {
                                "amount",
                                "value",
                                "reported",
                                "total",
                                "tax",
                                "cash",
                                "paid",
                                "change",
                            }
                        ]

                        value = find_value(
                            values,
                            safe_aliases,
                        )

                        if value is not None:
                            summary_values[field_name] = value

                    # -------------------------------------------------
                    # Exact label matching for summary rows
                    # -------------------------------------------------

                    label_normalized = re.sub(
                        r"\([^)]*\)",
                        "",
                        label.lower(),
                    )

                    label_normalized = re.sub(
                        r"[^a-z0-9]+",
                        "",
                        label_normalized,
                    )

                    for field_name, aliases in summary_aliases.items():

                        # Tax is handled separately below.
                        if field_name == "tax":
                            continue

                        for alias in aliases:

                            alias_normalized = (
                                alias.lower()
                                .replace(" ", "")
                                .replace("_", "")
                                .replace(".", "")
                            )

                            if (
                                label_normalized == alias_normalized
                                and values
                            ):
                                value = find_value(
                                    values,
                                    [
                                        "value",
                                        "amount",
                                        "total",
                                        "reported",
                                    ],
                                )

                                if value is not None:
                                    summary_values[field_name] = value

                    # -------------------------------------------------
                    # Explicit total tax from tax-summary tables
                    # -------------------------------------------------

                    total_tax_amount = find_value(
                        values,
                        [
                            "total_tax_amount",
                            "total tax amount",
                            "total_tax",
                            "total tax",
                        ],
                    )

                    if total_tax_amount is not None:
                        explicit_total_tax = total_tax_amount

                    # -------------------------------------------------
                    # Collect individual tax components
                    # -------------------------------------------------

                    tax_label_keywords = [
                        "tax payable",
                        "tax amount",
                        "tax",
                        "gst payable",
                        "gst amount",
                        "cgst",
                        "sgst",
                        "igst",
                        "vat payable",
                        "vat amount",
                        "sales tax",
                        "hst",
                    ]

                    is_total_label = (
                        "total" in label_normalized
                        or "subtotal" in label_normalized
                    )

                    is_tax_label = any(
                        keyword.replace(" ", "") in label_normalized
                        for keyword in tax_label_keywords
                    )

                    if (
                        is_tax_label
                        and not is_total_label
                    ):
                        tax_value = find_value(
                            values,
                            [
                                "amount",
                                "tax",
                                "tax(rm)",
                                "tax rm",
                                "value",
                                "reported",
                            ],
                        )

                        tax_number = _to_number(tax_value)

                        if tax_number is not None:
                            tax_component_values.append(
                                tax_number
                            )

            # -------------------------------------------------
            # Determine invoice tax
            #
            # Prefer an explicitly reported total tax amount.
            # Otherwise sum individual tax components.
            # -------------------------------------------------

            if explicit_total_tax is not None:

                summary_values["tax"] = (
                    explicit_total_tax
                )

            elif tax_component_values:

                summary_values["tax"] = sum(
                    tax_component_values
                )

    # ---------------------------------------------------------
    # 1. Quantity × Unit Price ≈ Line Total
    # ---------------------------------------------------------

    for index, item in enumerate(line_items, start=1):

        quantity = item["quantity"]
        unit_price = item["unit_price"]
        line_total = item["line_total"]

        calculated = None

        quantity_number = _to_number(quantity)
        unit_price_number = _to_number(unit_price)

        discount_percent = _to_number(
            item.get("discount_percent")
        )

        if (
            quantity_number is not None
            and unit_price_number is not None
        ):
            calculated = (
                quantity_number * unit_price_number
            )

            # Apply an explicitly reported discount.
            # Never infer a discount when it is absent.
            if discount_percent is not None:
                calculated = calculated * (
                    1 - discount_percent / 100
                )
        results.append(
            _compare(
                check_name=(
                    f"Line item {index}: "
                    "Quantity × Unit Price = Line Total"
                ),
                formula="quantity × unit_price = line_total",
                inputs={
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "discount_percent": item.get(
                    "discount_percent"
                    ),
                    "line_total": line_total,
                },
                calculated=calculated,
                reported=line_total,
            )
        )

    # ---------------------------------------------------------
    # 2. Sum of line totals ≈ subtotal / taxable amount
    # ---------------------------------------------------------

    line_total_numbers = []

    for item in line_items:

        value = _to_number(item["line_total"])

        if value is not None:
            line_total_numbers.append(value)

    line_sum = None

    if line_total_numbers:
        line_sum = sum(line_total_numbers)

    subtotal = summary_values.get("subtotal")

    if subtotal is None:
        subtotal = summary_values.get("taxable_amount")

    # Reconcile line totals against the most appropriate
    # reported invoice total.
    #
    # Some invoices show line-item totals as tax-inclusive.
    # In that case:
    #
    #   sum(line totals) = final total
    #
    # rather than:
    #
    #   sum(line totals) = taxable/subtotal

    line_reconciliation_reported = subtotal
    line_reconciliation_name = "Sum of line totals = Subtotal"
    line_reconciliation_formula = "sum(line_totals) = subtotal"

    final_total_number = _to_number(
        summary_values.get("total")
    )

    subtotal_number = _to_number(subtotal)

    if (
        line_sum is not None
        and final_total_number is not None
        and subtotal_number is not None
        and abs(line_sum - final_total_number) <= TOLERANCE
        and abs(line_sum - subtotal_number) > TOLERANCE
    ):
        # Line items already reconcile to the final total.
        # The difference is explained by tax.
        line_reconciliation_reported = summary_values.get("total")
        line_reconciliation_name = (
            "Sum of line totals = Total"
        )
        line_reconciliation_formula = (
            "sum(line_totals) = total"
        )

    results.append(
        _compare(
            check_name=line_reconciliation_name,
            formula=line_reconciliation_formula,
            inputs={
                "line_totals": [
                    item["line_total"]
                    for item in line_items
                ],
                "reported_total": line_reconciliation_reported,
                "subtotal": subtotal,
                "total": summary_values.get("total"),
            },
            calculated=line_sum,
            reported=line_reconciliation_reported,
        )
    )

    # ---------------------------------------------------------
    # 3. Taxable Amount + Tax ≈ Total
    # ---------------------------------------------------------

    # ---------------------------------------------------------
    # 3. Taxable Amount + Tax + Round Off ≈ Total
    # ---------------------------------------------------------

    taxable_amount = summary_values.get(
        "taxable_amount"
    )

    if taxable_amount is None:
        taxable_amount = summary_values.get(
            "subtotal"
        )

    tax = summary_values.get("tax")
    total = summary_values.get("total")

    discount = summary_values.get("discount")
    round_off = summary_values.get("round_off")

    taxable_number = _to_number(
        taxable_amount
    )

    tax_number = _to_number(
        tax
    )

    round_off_number = _to_number(
        round_off
    )

    discount_number = _to_number(
    discount
    )

    calculated_total = None

    if (
        taxable_number is not None
        and tax_number is not None
        and total is not None
    ):
        calculated_total = (
            taxable_number
            + tax_number
            + (discount_number or 0)
            + (round_off_number or 0)
        )

    results.append(
        _compare(
            check_name=(
                "taxable_amount + tax "
                 "+ discount + round_off = total"
            ),
            formula=(
                "taxable_amount + tax "
                "+ discount + round_off = total"
            ),
            inputs={
                "taxable_amount": taxable_amount,
                "tax": tax,
                "discount": discount,
                "round_off": round_off,
                "total": total,
            },
            calculated=calculated_total,
            reported=total,
        )
    )

    # ---------------------------------------------------------
    # 4. Cash Paid - Total ≈ Change
    # ---------------------------------------------------------

    cash_paid = summary_values.get("cash_paid")
    change = summary_values.get("change")

    cash_number = _to_number(cash_paid)
    total_number = _to_number(total)

    calculated_change = None

    if (
        cash_number is not None
        and total_number is not None
    ):
        calculated_change = (
            cash_number - total_number
        )

    results.append(
        _compare(
            check_name="Cash Paid - Total = Change",
            formula="cash_paid - total = change",
            inputs={
                "cash_paid": cash_paid,
                "total": total,
                "change": change,
            },
            calculated=calculated_change,
            reported=change,
        )
    )

    return {
        "checks": results,
        "overall_status": (
            "FAILED"
            if any(
                check["status"] == "FAIL"
                for check in results
            )
            else "PASS"
        ),
    }


def validate_balance_sheet(
    extracted_data: dict[str, Any],
) -> dict[str, Any]:

    checks = []

    financial_statement = extracted_data.get(
        "financial_statement",
        {}
    )

    sections = financial_statement.get(
        "sections",
        []
    )

    periods = extracted_data.get(
        "comparative_periods",
        []
    )

    def get_section(
        section_name: str,
    ) -> list[dict[str, Any]]:

        if not isinstance(sections, list):
            return []

        for section in sections:

            if not isinstance(section, dict):
                continue

            current_name = str(
                section.get("section_name", "")
            ).strip().lower()

            if current_name == section_name.lower():

                line_items = section.get(
                    "line_items",
                    []
                )

                if isinstance(line_items, list):
                    return line_items

        return []

    def find_line_item(
        section: list[dict[str, Any]],
        line_item_name: str,
        period: str,
    ) -> Any:

        for item in section:

            if not isinstance(item, dict):
                continue

            current_name = str(
                item.get("line_item", "")
            ).strip().lower()

            if current_name == line_item_name.lower():

                values = item.get(
                    "values",
                    {}
                )

                if isinstance(values, dict):
                    return values.get(period)

        return None

    def find_total(
        section: list[dict[str, Any]],
        period: str,
    ) -> Any:

        return find_line_item(
            section,
            "total",
            period,
        )

    def calculate_component_sum(
        section: list[dict[str, Any]],
        component_names: list[str],
        period: str,
    ) -> tuple[float | None, dict[str, Any]]:

        inputs = {}
        numeric_values = []

        for component_name in component_names:

            value = find_line_item(
                section,
                component_name,
                period,
            )

            inputs[component_name] = value

            number = _to_number(value)

            if number is None:
                return None, inputs

            numeric_values.append(number)

        return sum(numeric_values), inputs

    capital_data = get_section(
        "CAPITAL AND LIABILITIES"
    )

    assets_data = get_section(
        "ASSETS"
    )

    def get_numeric_component_names(
    line_items,
    period,
):
        component_names = []

        for item in line_items:

            line_item = item.get("line_item")

            # Stop at the reported Total.
            # Anything after Total is not part of
            # the component sum.
            if line_item == "Total":
                break

            values = item.get("values", {})

            value = values.get(period)

            if value is not None:
                component_names.append(line_item)

        return component_names

    for period in periods:

        capital_components = (
            get_numeric_component_names(
                capital_data,
                period,
            )
        )

        asset_components = (
            get_numeric_component_names(
                assets_data,
                period,
            )
        )
        # ---------------------------------
        # 1. Capital & Liabilities
        # component sum = reported total
        # ---------------------------------

        capital_calculated, capital_inputs = (
            calculate_component_sum(
                capital_data,
                capital_components,
                period,
            )
        )

        capital_reported = find_total(
            capital_data,
            period,
        )

        checks.append(
            _compare(
                check_name=(
                    "Capital & Liabilities "
                    f"Component Sum - {period}"
                ),
                formula=(
                    "Capital + Reserves and surplus "
                    "+ Minority interest + Deposits "
                    "+ Borrowings "
                    "+ Other liabilities and provisions "
                    "= Total Capital & Liabilities"
                ),
                inputs={
                    "period": period,
                    "components": capital_inputs,
                },
                calculated=capital_calculated,
                reported=capital_reported,
            )
        )

        # ---------------------------------
        # 2. Assets
        # component sum = reported total
        # ---------------------------------

        assets_calculated, assets_inputs = (
            calculate_component_sum(
                assets_data,
                asset_components,
                period,
            )
        )

        assets_reported = find_total(
            assets_data,
            period,
        )

        checks.append(
            _compare(
                check_name=(
                    "Assets Component Sum "
                    f"- {period}"
                ),
                formula=(
                    "Cash and balances with RBI "
                    "+ Balances with banks "
                    "+ Investments "
                    "+ Advances "
                    "+ Fixed assets "
                    "+ Other assets "
                    "= Total Assets"
                ),
                inputs={
                    "period": period,
                    "components": assets_inputs,
                },
                calculated=assets_calculated,
                reported=assets_reported,
            )
        )

        # ---------------------------------
        # 3. Balance Sheet Equation
        # Capital & Liabilities = Assets
        # ---------------------------------

        capital_total = find_total(
            capital_data,
            period,
        )

        assets_total = find_total(
            assets_data,
            period,
        )

        checks.append(
            _compare(
                check_name=(
                    f"Balance Sheet Equation - {period}"
                ),
                formula=(
                    "Capital & Liabilities = Assets"
                ),
                inputs={
                    "period": period,
                    "capital_and_liabilities": (
                        capital_total
                    ),
                    "assets": assets_total,
                },
                calculated=capital_total,
                reported=assets_total,
            )
        )

    statuses = [
        check["status"]
        for check in checks
    ]

    if "FAIL" in statuses:

        overall_status = "FAIL"

    elif (
        not checks
        or "NOT_APPLICABLE" in statuses
    ):

        overall_status = "NOT_APPLICABLE"

    else:

        overall_status = "PASS"

    return {
        "status": overall_status,
        "checks": checks,
    }

def validate_profit_and_loss(
    extracted_data: dict[str, Any],
) -> dict[str, Any]:

    checks = []

    financial_statement = extracted_data.get(
        "financial_statement",
        {}
    )

    periods = extracted_data.get(
        "comparative_periods",
        []
    )

    sections = financial_statement.get(
        "sections",
        []
    )

    def get_section(section_name: str) -> list:
        def normalize(value: str) -> str:
            return (
                str(value)
                .strip()
                .lower()
                .replace(".", "")
                .replace(":", "")
                .replace("-", "")
                .replace("_", "")
                .replace(" ", "")
            )

        target = normalize(section_name)

        for section in sections:
            if not isinstance(section, dict):
                continue

            name = normalize(
                section.get("section_name", "")
            )

            # Exact match
            if name == target:
                return section.get("line_items", [])

            # Allow numbered/prefixed sections:
            # "I. INCOME" -> "INCOME"
            # "II. EXPENDITURE" -> "EXPENDITURE"
            # "III. PROFIT" -> "PROFIT"
            if name.endswith(target):
                return section.get("line_items", [])

        return []
    def find_value(
        section: list,
        line_item_name: str | list[str],
        period: str,
    ) -> Any:

        def normalize_label(value: str) -> str:
            return (
                str(value)
                .strip()
                .lower()
                .replace(":", "")
                .replace(",", "")
                .replace("'", "")
                .replace("’", "")
                .replace(" ", "")
            )

        if isinstance(line_item_name, str):
            targets = [normalize_label(line_item_name)]
        else:
            targets = [
                normalize_label(label)
                for label in line_item_name
            ]

        for item in section:
            if not isinstance(item, dict):
                continue

            name = normalize_label(
                item.get("line_item", "")
            )

            if name in targets:
                values = item.get("values", {})

                if isinstance(values, dict):
                    return values.get(period)

        return None
    income_section = get_section("INCOME")
    expenditure_section = get_section("EXPENDITURE")
    profit_section = get_section("PROFIT")

    for period in periods:

        # -----------------------------
        # TOTAL INCOME
        # -----------------------------

        interest_earned = find_value(
            income_section,
            "Interest earned",
            period,
        )

        other_income = find_value(
            income_section,
            "Other income",
            period,
        )

        total_income = find_value(
            income_section,
            "Total",
            period,
        )

        interest_earned_number = _to_number(
            interest_earned
        )

        other_income_number = _to_number(
            other_income
        )

        income_calculated = None

        if (
            interest_earned_number is not None
            and other_income_number is not None
        ):
            income_calculated = (
                interest_earned_number
                + other_income_number
            )

        checks.append(
            _compare(
                check_name=f"Total Income Reconciliation - {period}",
                formula=(
                    "Interest Earned + Other Income = Total Income"
                ),
                inputs={
                    "period": period,
                    "interest_earned": interest_earned,
                    "other_income": other_income,
                    "total_income": total_income,
                },
                calculated=income_calculated,
                reported=total_income,
            )
        )

        # -----------------------------
        # TOTAL EXPENDITURE
        # -----------------------------

        interest_expended = find_value(
            expenditure_section,
            "Interest expended",
            period,
        )

        operating_expenses = find_value(
            expenditure_section,
            "Operating expenses",
            period,
        )

        provisions = find_value(
            expenditure_section,
            [
                "Provisions and contingencies",
                "Provisions and contingencies [Refer Schedule 18 (11)]",
                "Provisions and contingencies [Refer Schedule 18 (15)]",
            ],
            period,
        )

        total_expenditure = find_value(
            expenditure_section,
            "Total",
            period,
        )

        interest_expended_number = _to_number(
            interest_expended
        )

        operating_expenses_number = _to_number(
            operating_expenses
        )

        provisions_number = _to_number(
            provisions
        )

        expenditure_calculated = None

        if (
            interest_expended_number is not None
            and operating_expenses_number is not None
            and provisions_number is not None
        ):
            expenditure_calculated = (
                interest_expended_number
                + operating_expenses_number
                + provisions_number
            )

        checks.append(
            _compare(
                check_name=f"Total Expenditure Reconciliation - {period}",
                formula=(
                    "Interest Expended + Operating Expenses "
                    "+ Provisions and Contingencies = Total Expenditure"
                ),
                inputs={
                    "period": period,
                    "interest_expended": interest_expended,
                    "operating_expenses": operating_expenses,
                    "provisions_and_contingencies": provisions,
                    "total_expenditure": total_expenditure,
                },
                calculated=expenditure_calculated,
                reported=total_expenditure,
            )
        )

        # -----------------------------
        # NET PROFIT
        # -----------------------------

        net_profit = find_value(
            profit_section,
            [
                "Net profit for the year",
                "Consolidated Net Profit for the year before minorities' interest",
                "Consolidated Net Profit for the year before Minority Interest",
            ],
            period,
        )

        total_income_number = _to_number(
            total_income
        )

        total_expenditure_number = _to_number(
            total_expenditure
        )

        net_profit_calculated = None

        if (
            total_income_number is not None
            and total_expenditure_number is not None
        ):
            net_profit_calculated = (
                total_income_number
                - total_expenditure_number
            )

        checks.append(
            _compare(
                check_name=f"Net Profit Reconciliation - {period}",
                formula=(
                    "Total Income - Total Expenditure = Net Profit"
                ),
                inputs={
                    "period": period,
                    "total_income": total_income,
                    "total_expenditure": total_expenditure,
                    "net_profit": net_profit,
                },
                calculated=net_profit_calculated,
                reported=net_profit,
            )
        )

        # -----------------------------
        # CONSOLIDATED PROFIT
        # -----------------------------

        minority_interest = find_value(
            profit_section,
            [
                "Less: Minority interest",
                "Less : Minorities' Interest",
                "Less : Minority interest",
            ],
            period,
        )

        associate_profit = find_value(
            profit_section,
            "Add: Share in profits of associates",
            period,
        )

        consolidated_profit = find_value(
            profit_section,
            [
                "Consolidated profit for the year attributable to the Group",
                "Consolidated Net Profit for the year attributable to the group",
                "Consolidated profit for the year"
            ],
            period,
        )

        net_profit_number = _to_number(
            net_profit
        )

        minority_interest_number = _to_number(
            minority_interest
        )

        associate_profit_number = _to_number(
            associate_profit
        )

        consolidated_profit_calculated = None

        if (
            net_profit_number is not None
            and minority_interest_number is not None
        ):
            consolidated_profit_calculated = (
                net_profit_number
                - minority_interest_number
            )

        checks.append(
            _compare(
                check_name=f"Consolidated Profit Reconciliation - {period}",
                formula=(
                    "Net Profit - Minority Interest "
                    "= Consolidated Profit Attributable to Group"
                ),
                inputs={
                    "period": period,
                    "net_profit": net_profit,
                    "minority_interest": minority_interest,
                    "share_in_profits_of_associates": associate_profit,
                    "consolidated_profit_attributable_to_group": consolidated_profit,
                },
                calculated=consolidated_profit_calculated,
                reported=consolidated_profit,
            )
        )

        amalgamation_adjustment = find_value(
            profit_section,
            [
            "Impact on amalgamation [Refer Schedule 18(1)]",
            "Amalgamation adjustment",
            "Addition on amalgamation (net)",],
            period,
            
        )

        brought_forward = find_value(
            profit_section,
            [
                "Balance in Profit and Loss account brought forward",
                "Add: Brought forward consolidated profit attributable to the group",
                "Balance in the Profit and Loss Account brought forward",
                "Brought forward consolidated profit attributable to the group"
            ],
            period,
        )

        total_available = find_value(
            profit_section,
            "Total",
            period,
        )

        consolidated_profit_number = _to_number(
            consolidated_profit
        )
        amalgamation_number = _to_number(
            amalgamation_adjustment
        )
        brought_forward_number = _to_number(
            brought_forward
        )

        appropriation_calculated = None

        if (
            consolidated_profit_number is not None
            and brought_forward_number is not None
        ):
            adjustment = 0

            if amalgamation_number is not None:
                adjustment = amalgamation_number

            appropriation_calculated = (
                consolidated_profit_number
                + adjustment
                + brought_forward_number
            )

        checks.append(
            _compare(
                check_name=f"Total Available for Appropriation Reconciliation - {period}",
                formula=(
                    "Consolidated Profit Attributable to Group "
                    "+ Applicable Amalgamation Adjustment "
                    "+ Brought Forward Profit "
                    "= Total Available for Appropriation"
                ),
                inputs={
                    "period": period,
                    "consolidated_profit_attributable_to_group": consolidated_profit,
                    "amalgamation_adjustment": amalgamation_adjustment,
                    "brought_forward_profit": brought_forward,
                    "total_available_for_appropriation": total_available,
                },
                calculated=appropriation_calculated,
                reported=total_available,
            )
        )

    statuses = [check["status"] for check in checks]

    if "FAIL" in statuses:
        overall_status = "FAIL"
    elif not checks or "NOT_APPLICABLE" in statuses:
        overall_status = "NOT_APPLICABLE"
    else:
        overall_status = "PASS"

    return {
        "status": overall_status,
        "checks": checks,
    }


def validate_cash_flow(
    extracted_data: dict[str, Any],
) -> dict[str, Any]:

    financial_statement = extracted_data.get(
        "financial_statement",
        {}
    )

    sections = financial_statement.get(
        "sections",
        []
    )

    # ---------------------------------------------------------
    # Collect all line items from all sections
    # ---------------------------------------------------------

    line_items = []

    for section in sections:

        for item in section.get(
            "line_items",
            []
        ):

            line_items.append(item)

    # ---------------------------------------------------------
    # Get periods from extracted document
    # ---------------------------------------------------------

    periods = extracted_data.get(
        "comparative_periods",
        []
    )

    # Fallback: collect periods from line-item values
    if not periods:

        period_set = set()

        for item in line_items:

            values = item.get(
                "values",
                {}
            )

            if isinstance(values, dict):
                period_set.update(
                    values.keys()
                )

        periods = list(period_set)

    # ---------------------------------------------------------
    # Normalize labels for flexible matching
    # ---------------------------------------------------------

    def normalize_label(label: Any) -> str:

        if label is None:
            return ""

        return (
            str(label)
            .lower()
            .replace("/", " ")
            .replace("-", " ")
            .replace("(", " ")
            .replace(")", " ")
            .replace(",", " ")
            .replace(".", " ")
        )

    # ---------------------------------------------------------
    # Find a line item using keyword patterns
    # ---------------------------------------------------------

    def find_line_item(
        patterns: list[list[str]],
    ) -> dict | None:

        for item in line_items:

            label = normalize_label(
                item.get("line_item")
            )

            for pattern_group in patterns:

                if all(
                    keyword in label
                    for keyword in pattern_group
                ):
                    return item

        return None

    # ---------------------------------------------------------
    # Extract value for a particular period
    # ---------------------------------------------------------

    def get_value(
        item: dict | None,
        period: str,
    ):

        if item is None:
            return None

        values = item.get(
            "values",
            {}
        )

        if not isinstance(values, dict):
            return None

        return values.get(period)

    # ---------------------------------------------------------
    # Locate required Cash Flow rows
    # ---------------------------------------------------------

    operating_item = find_line_item(
        [
            ["net", "cash", "operating", "activities"],
        ]
    )

    investing_item = find_line_item(
        [
            ["net", "cash", "investing", "activities"],
        ]
    )

    financing_item = find_line_item(
        [
            ["net", "cash", "financing", "activities"],
        ]
    )

    fx_item = find_line_item(
    [
        ["effect", "exchange", "fluctuation"],
        ["exchange", "fluctuation", "translation"],
        ["exchange", "translation"],
        ["effect", "fluctuation", "foreign", "currency", "translation"],
        ["foreign", "currency", "translation", "reserve"],
    ]
)

    net_change_item = find_line_item(
        [
            ["net", "increase", "cash", "cash", "equivalents"],
            ["net", "decrease", "cash", "cash", "equivalents"],
        ]
    )

    opening_cash_item = find_line_item(
        [
            ["cash", "cash", "equivalents", "april"],
            ["cash", "cash", "equivalents", "opening"],
            ["cash", "cash", "equivalents", "beginning"],
        ]
    )

    closing_cash_item = find_line_item(
    [
        ["cash", "cash", "equivalents", "march"],
        ["cash", "cash", "equivalents", "closing"],
        ["cash", "cash", "equivalents", "ending"],
        ["cash", "cash", "equivalents", "end", "year"],
    ]
)

    # ---------------------------------------------------------
    # Cash acquired / amalgamation / other applicable
    # adjustment
    # ---------------------------------------------------------

    acquisition_item = find_line_item(
        [
            ["cash", "cash", "equivalents", "amalgamation"],
            ["cash", "acquired", "amalgamation"],
            ["cash", "acquired"],
        ]
    )

    checks = []

    # ---------------------------------------------------------
    # Validate every comparative period independently
    # ---------------------------------------------------------

    for period in periods:

        operating = get_value(
            operating_item,
            period,
        )

        investing = get_value(
            investing_item,
            period,
        )

        financing = get_value(
            financing_item,
            period,
        )

        fx_adjustment = get_value(
            fx_item,
            period,
        )

        net_change = get_value(
            net_change_item,
            period,
        )

        opening_cash = get_value(
            opening_cash_item,
            period,
        )

        closing_cash = get_value(
            closing_cash_item,
            period,
        )

        acquisition_adjustment = get_value(
            acquisition_item,
            period,
        )

        # -----------------------------------------------------
        # First reconciliation:
        #
        # Operating + Investing + Financing + FX
        # + applicable cash adjustment
        # = Net Increase / Decrease
        # -----------------------------------------------------

        operating_number = _to_number(
            operating
        )

        investing_number = _to_number(
            investing
        )

        financing_number = _to_number(
            financing
        )

        fx_number = _to_number(
            fx_adjustment
        )

        acquisition_number = _to_number(
            acquisition_adjustment
        )

        net_change_number = _to_number(
            net_change
        )

        activity_calculated = None

        if (
            operating_number is not None
            and investing_number is not None
            and financing_number is not None
            and net_change_number is not None
        ):

            # Missing FX means there is no separately
            # reported FX adjustment.
            fx_value = (
                fx_number
                if fx_number is not None
                else 0
            )

            base_calculated = (
                operating_number
                + investing_number
                + financing_number
                + fx_value
            )

            # Some statements, such as the 2017 format,
            # report cash acquired/on amalgamation separately
            # but include it in the reported net change.
            #
            # Add it only when required to reconcile.
            if acquisition_number is not None:

                base_variance = (
                    base_calculated
                    - net_change_number
                )

                adjusted_calculated = (
                    base_calculated
                    + acquisition_number
                )

                adjusted_variance = (
                    adjusted_calculated
                    - net_change_number
                )

                if (
                    abs(adjusted_variance)
                    <= TOLERANCE
                ):

                    activity_calculated = (
                        adjusted_calculated
                    )

                else:

                    activity_calculated = (
                        base_calculated
                    )

            else:

                activity_calculated = (
                    base_calculated
                )

        checks.append(
            _compare(
                check_name=(
                    "Cash Flow Activity Reconciliation "
                    f"- {period}"
                ),
                formula=(
                    "Operating Cash Flow "
                    "+ Investing Cash Flow "
                    "+ Financing Cash Flow "
                    "+ FX / Translation Adjustment "
                    "+ Applicable Cash Acquisition Adjustment "
                    "= Net Increase / (Decrease) "
                    "in Cash & Cash Equivalents"
                ),
                inputs={
                    "period": period,
                    "operating_cash_flow": operating,
                    "investing_cash_flow": investing,
                    "financing_cash_flow": financing,
                    "fx_translation_adjustment": fx_adjustment,
                    "cash_acquisition_adjustment": (
                        acquisition_adjustment
                    ),
                    "net_change_in_cash": net_change,
                },
                calculated=activity_calculated,
                reported=net_change,
            )
        )

        # -----------------------------------------------------
        # Second reconciliation:
        #
        # Opening Cash + Net Change = Closing Cash
        #
        # If an applicable cash-acquisition adjustment is NOT
        # already included in net change, try including it.
        # -----------------------------------------------------

        opening_number = _to_number(
            opening_cash
        )

        closing_number = _to_number(
            closing_cash
        )

        closing_calculated = None

        if (
            opening_number is not None
            and net_change_number is not None
            and closing_number is not None
        ):

            base_closing = (
                opening_number
                + net_change_number
            )

            base_variance = (
                base_closing
                - closing_number
            )

            # Normally the reported Net Increase already
            # includes all applicable adjustments.
            if (
                abs(base_variance)
                <= TOLERANCE
            ):

                closing_calculated = (
                    base_closing
                )

            elif acquisition_number is not None:

                adjusted_closing = (
                    opening_number
                    + net_change_number
                    + acquisition_number
                )

                adjusted_variance = (
                    adjusted_closing
                    - closing_number
                )

                if (
                    abs(adjusted_variance)
                    <= TOLERANCE
                ):

                    closing_calculated = (
                        adjusted_closing
                    )

                else:

                    closing_calculated = (
                        base_closing
                    )

            else:

                closing_calculated = (
                    base_closing
                )

        checks.append(
            _compare(
                check_name=(
                    "Opening to Closing Cash Reconciliation "
                    f"- {period}"
                ),
                formula=(
                    "Opening Cash & Cash Equivalents "
                    "+ Net Increase / (Decrease) in Cash "
                    "+ Applicable Adjustment if required "
                    "= Closing Cash & Cash Equivalents"
                ),
                inputs={
                    "period": period,
                    "opening_cash": opening_cash,
                    "net_change_in_cash": net_change,
                    "cash_acquisition_adjustment": (
                        acquisition_adjustment
                    ),
                    "closing_cash": closing_cash,
                },
                calculated=closing_calculated,
                reported=closing_cash,
            )
        )

    # ---------------------------------------------------------
    # Overall status
    # ---------------------------------------------------------

    statuses = [
        check["status"]
        for check in checks
    ]

    if "FAIL" in statuses:

        overall_status = "FAIL"

    elif (
        not checks
        or "NOT_APPLICABLE" in statuses
    ):

        overall_status = "NOT_APPLICABLE"

    else:

        overall_status = "PASS"

    return {
        "status": overall_status,
        "checks": checks,
    }