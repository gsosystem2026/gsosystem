"""Phase 6.3 / 6.4: Excel export for IPMT and WAR using openpyxl."""
import io
import os
from datetime import date

from django.conf import settings
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter

from .war_config import get_war_table_config


def _month_range(year: int, month: int):
    """First and last day of the given month."""
    start = date(year, month, 1)
    if month == 12:
        end = date(year, 12, 31)
    else:
        end = date(year, month + 1, 1)
    from datetime import timedelta
    end = end - timedelta(days=1)
    return start, end


def build_ipmt_excel(personnel, year: int, month: int):
    """
    Build IPMT Excel: WARs for the given personnel where period overlaps the given month.
    Columns: Request ID, Period Start, Period End, Summary, Accomplishments, Success Indicators.
    """
    from .models import WorkAccomplishmentReport
    start, end = _month_range(year, month)
    # WARs where personnel matches and (period_start <= end and period_end >= start)
    qs = WorkAccomplishmentReport.objects.filter(
        personnel=personnel,
        period_start__lte=end,
        period_end__gte=start,
    ).select_related('request', 'personnel').prefetch_related('success_indicators').order_by('period_start')
    return _war_list_to_excel(
        qs,
        title=f"IPMT Report — {personnel.get_full_name() or personnel.username} — {year}-{month:02d}",
        sheet_name=f"IPMT {year}-{month:02d}",
    )


def build_war_export_excel(queryset, title="WAR Export", unit=None):
    """Build WAR export Excel. Per-unit structure: Repair & Maintenance = 9 cols + orange header; All units = 12 cols generic."""
    _config_key, config = get_war_table_config(unit)
    return _war_list_to_excel(
        queryset,
        title=title,
        sheet_name="WAR",
        unit=unit,
        table_config=config,
    )


def _format_period_range(queryset):
    """Return a string like 'AUGUST 1-31, 2025' from queryset min/max period dates."""
    if not queryset:
        return ""
    starts = [w.period_start for w in queryset]
    ends = [w.period_end for w in queryset]
    d_start = min(starts)
    d_end = max(ends)
    if d_start.month == d_end.month and d_start.year == d_end.year:
        return f"{d_start.strftime('%B').upper()} {d_start.day}-{d_end.day}, {d_start.year}"
    return f"{d_start.strftime('%B %d, %Y').upper()} – {d_end.strftime('%B %d, %Y').upper()}"


def _war_list_to_excel(queryset, title="WAR", sheet_name="WAR", unit=None, table_config=None):
    """
    Write WAR queryset to an openpyxl workbook. Uses table_config for headers and column count;
    if None, uses generic config from get_war_table_config(unit).
    Returns (buf, filename_suffix).
    """
    if table_config is None:
        _, table_config = get_war_table_config(unit)
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name[:31]
    bold_center = Font(bold=True, size=11)
    bold_title = Font(bold=True, size=14)
    center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

    # Rows 1–5: institutional header — PSU logo (left), centered text (middle), GSO logo (right)
    header_texts = [
        "Republic of the Philippines",
        "PALAWAN STATE UNIVERSITY",
        "ADMINISTRATIVE DIVISION",
        "GENERAL SERVICES OFFICE",
        "Puerto Princesa City",
    ]
    for r in range(1, 6):
        ws.row_dimensions[r].height = 18
    for r, text in enumerate(header_texts, start=1):
        ws.cell(row=r, column=3, value=text)
        ws.cell(row=r, column=3).font = bold_center
        ws.cell(row=r, column=3).alignment = center_align
        ws.merge_cells(start_row=r, start_column=3, end_row=r, end_column=8)
    # Logos beside the text block (left A1, right I1), height ~5 rows
    base = getattr(settings, 'BASE_DIR', None)
    if base is not None:
        try:
            psu_path = base / 'static' / 'img' / 'logo' / 'psu_logo.png'
            gso_path = base / 'static' / 'img' / 'logo' / 'gso_logo.png'
        except TypeError:
            psu_path = os.path.join(base, 'static', 'img', 'logo', 'psu_logo.png')
            gso_path = os.path.join(base, 'static', 'img', 'logo', 'gso_logo.png')
    else:
        psu_path = gso_path = None
    try:
        from openpyxl.drawing.image import Image
        logo_height_px = 90  # ~5 rows at 18pt so logos align with text block
        if psu_path is not None and os.path.isfile(str(psu_path)):
            img_psu = Image(str(psu_path))
            w_orig, h_orig = img_psu.width, img_psu.height
            img_psu.height = logo_height_px
            img_psu.width = int(w_orig * (logo_height_px / h_orig))
            ws.add_image(img_psu, 'A1')
        else:
            ws.cell(row=1, column=1, value="[Insert PSU logo here]")
            ws.cell(row=1, column=1).font = Font(italic=True, size=9, color="808080")
        if gso_path is not None and os.path.isfile(str(gso_path)):
            img_gso = Image(str(gso_path))
            w_orig, h_orig = img_gso.width, img_gso.height
            img_gso.height = logo_height_px
            img_gso.width = int(w_orig * (logo_height_px / h_orig))
            ws.add_image(img_gso, 'I1')
        else:
            ws.cell(row=1, column=9, value="[Insert GSO logo here]")
            ws.cell(row=1, column=9).font = Font(italic=True, size=9, color="808080")
    except Exception:
        ws.cell(row=1, column=1, value="[Insert PSU logo here]")
        ws.cell(row=1, column=1).font = Font(italic=True, size=9, color="808080")
        ws.cell(row=1, column=9, value="[Insert GSO logo here]")
        ws.cell(row=1, column=9).font = Font(italic=True, size=9, color="808080")
    # Row 6: blank
    # Row 7: WORK ACCOMPLISHMENT REPORT
    ws.cell(row=7, column=1, value="WORK ACCOMPLISHMENT REPORT")
    ws.cell(row=7, column=1).font = bold_title
    ws.cell(row=7, column=1).alignment = center_align
    ws.merge_cells(start_row=7, start_column=1, end_row=7, end_column=9)
    # Row 8: Reporting period
    period_label = _format_period_range(queryset) if queryset else ""
    ws.cell(row=8, column=1, value=f"Reporting period: {period_label}" if period_label else "Reporting period: —")
    ws.cell(row=8, column=1).alignment = center_align
    ws.merge_cells(start_row=8, start_column=1, end_row=8, end_column=9)
    # Row 9: Unit
    unit_name = (unit.name.upper() if unit else "ALL UNITS").replace(" ", " ")
    ws.cell(row=9, column=1, value=f"Unit: {unit_name}")
    ws.cell(row=9, column=1).alignment = center_align
    ws.merge_cells(start_row=9, start_column=1, end_row=9, end_column=9)
    # Row 10: blank
    # Row 11: table headers (from table_config)
    headers = table_config['excel_headers']
    num_cols = table_config['excel_column_count']
    header_fill = table_config.get('header_fill')
    fill = PatternFill(start_color=header_fill, end_color=header_fill, fill_type='solid') if header_fill else None
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=11, column=col, value=h)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center", wrap_text=True)
        cell.border = thin_border
        if fill:
            cell.fill = fill
    data_start_row = 12
    row = data_start_row
    for war in queryset:
        req = war.request
        requestor = getattr(req, "requestor", None)
        requesting_office = ""
        if requestor:
            requesting_office = requestor.get_full_name() or getattr(requestor, "username", "") or ""
        total_materials = 0.0
        labor = 0.0
        total = total_materials + labor
        if num_cols == 12:
            # Generic (All units): Request ID, Unit, Personnel, Date Started, Date Completed, Name of Activity, Description, Requesting Office, Status, Total Materials, Labor, Total
            ws.cell(row=row, column=1, value=req.display_id() if hasattr(req, 'display_id') else str(req.pk))
            ws.cell(row=row, column=2, value=req.unit.name if req.unit_id else "")
            ws.cell(row=row, column=3, value=war.personnel.get_full_name() or getattr(war.personnel, 'username', ''))
            ws.cell(row=row, column=4, value=war.period_start)
            ws.cell(row=row, column=5, value=war.period_end)
            ws.cell(row=row, column=6, value=war.summary or "")
            ws.cell(row=row, column=7, value=war.accomplishments or "")
            ws.cell(row=row, column=8, value=requesting_office)
            ws.cell(row=row, column=9, value="Completed")
            ws.cell(row=row, column=10, value=total_materials)
            ws.cell(row=row, column=10).number_format = "#,##0.00"
            ws.cell(row=row, column=11, value=labor)
            ws.cell(row=row, column=11).number_format = "#,##0.00"
            ws.cell(row=row, column=12, value=total)
            ws.cell(row=row, column=12).number_format = "#,##0.00"
        elif num_cols == 9:
            # Repair & Maintenance (9 columns): Date Started, Date Completed, Name of Activity, Description, Requesting Office, Status, Total Materials, Labor, Total
            ws.cell(row=row, column=1, value=war.period_start)
            ws.cell(row=row, column=2, value=war.period_end)
            ws.cell(row=row, column=3, value=war.summary or "")
            ws.cell(row=row, column=4, value=war.accomplishments or "")
            ws.cell(row=row, column=5, value=requesting_office)
            ws.cell(row=row, column=6, value="Completed")
            ws.cell(row=row, column=7, value=total_materials)
            ws.cell(row=row, column=7).number_format = "#,##0.00"
            ws.cell(row=row, column=8, value=labor)
            ws.cell(row=row, column=8).number_format = "#,##0.00"
            ws.cell(row=row, column=9, value=total)
            ws.cell(row=row, column=9).number_format = "#,##0.00"
        else:
            # Electrical (10 columns): Date Started, Date Complete, Name of Project, Description, Requesting Office, Assigned Personnel, Status, Material Cost, Labor Cost, Total Cost
            personnel_name = war.personnel.get_full_name() or getattr(war.personnel, 'username', '')
            ws.cell(row=row, column=1, value=war.period_start)
            ws.cell(row=row, column=2, value=war.period_end)
            ws.cell(row=row, column=3, value=war.summary or "")
            ws.cell(row=row, column=4, value=war.accomplishments or "")
            ws.cell(row=row, column=5, value=requesting_office)
            ws.cell(row=row, column=6, value=personnel_name)
            ws.cell(row=row, column=7, value="Done")
            ws.cell(row=row, column=8, value=total_materials)
            ws.cell(row=row, column=8).number_format = "#,##0.00"
            ws.cell(row=row, column=9, value=labor)
            ws.cell(row=row, column=9).number_format = "#,##0.00"
            ws.cell(row=row, column=10, value=total)
            ws.cell(row=row, column=10).number_format = "#,##0.00"
        for c in range(1, num_cols + 1):
            ws.cell(row=row, column=c).border = thin_border
        row += 1
    # Column widths by layout
    if num_cols == 12:
        widths = [12, 18, 18, 14, 14, 22, 35, 18, 12, 14, 12, 18]
    elif num_cols == 9:
        widths = [14, 14, 22, 35, 18, 12, 14, 12, 18]
    else:
        widths = [14, 14, 20, 35, 18, 18, 10, 14, 12, 14]  # electrical 10 cols
    for col, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(col)].width = w
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf, title.replace(" ", "_")[:80]


def get_war_queryset(personnel=None, unit=None, date_from=None, date_to=None):
    """Return WorkAccomplishmentReport queryset filtered by optional personnel, unit, and date range."""
    from .models import WorkAccomplishmentReport
    qs = WorkAccomplishmentReport.objects.select_related(
        'request', 'personnel', 'request__unit', 'request__requestor',
    ).prefetch_related('success_indicators').order_by('-period_end', '-created_at')
    if personnel:
        qs = qs.filter(personnel=personnel)
    if unit:
        qs = qs.filter(request__unit=unit)
    if date_from:
        qs = qs.filter(period_end__gte=date_from)
    if date_to:
        qs = qs.filter(period_start__lte=date_to)
    return qs


def get_feedback_queryset(date_from=None, date_to=None, unit=None):
    """Return RequestFeedback queryset for Director/GSO reports. Optional date range and unit."""
    from apps.gso_requests.models import RequestFeedback
    qs = RequestFeedback.objects.select_related(
        'request', 'user', 'request__unit', 'request__requestor',
    ).order_by('-created_at')
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)
    if unit:
        qs = qs.filter(request__unit=unit)
    return qs


def build_feedback_export_excel(queryset):
    """Build Feedback (CSM) export Excel. Columns: Request ID, Unit, Requestor, Date, CC1-3, SQD1-9, Suggestions, Email."""
    from openpyxl.utils import get_column_letter
    wb = Workbook()
    ws = wb.active
    ws.title = "Feedback"[:31]
    headers = [
        "Request ID", "Unit", "Requestor", "Submitted",
        "CC1", "CC2", "CC3",
        "SQD1", "SQD2", "SQD3", "SQD4", "SQD5", "SQD6", "SQD7", "SQD8", "SQD9",
        "Suggestions", "Email",
    ]
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(wrap_text=True)
    row = 2
    for fb in queryset:
        req = fb.request
        cc1_display = dict(fb.CC1_CHOICES).get(fb.cc1, fb.cc1 or "")
        cc2_display = dict(fb.CC2_CHOICES).get(fb.cc2, fb.cc2 or "")
        cc3_display = dict(fb.CC3_CHOICES).get(fb.cc3, fb.cc3 or "")
        ws.cell(row=row, column=1, value=req.display_id)
        ws.cell(row=row, column=2, value=req.unit.name if req.unit_id else "")
        ws.cell(row=row, column=3, value=fb.user.get_full_name() or fb.user.username)
        ws.cell(row=row, column=4, value=fb.created_at)
        ws.cell(row=row, column=5, value=cc1_display)
        ws.cell(row=row, column=6, value=cc2_display)
        ws.cell(row=row, column=7, value=cc3_display)
        for i in range(1, 10):
            ws.cell(row=row, column=7 + i, value=getattr(fb, f'sqd{i}', None))
        ws.cell(row=row, column=17, value=fb.suggestions or "")
        ws.cell(row=row, column=18, value=fb.email or "")
        row += 1
    for col in range(1, len(headers) + 1):
        ws.column_dimensions[get_column_letter(col)].width = max(10, min(40, len(headers[col - 1]) + 2))
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf, "feedback"