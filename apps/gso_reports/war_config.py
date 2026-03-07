"""
Per-unit WAR table and Excel structure.
- All units: generic table (Request ID, Unit, Personnel, Period, Summary, Accomplishments, Success indicators)
  and generic Excel (includes Unit, Personnel; 12 columns).
- Repair & Maintenance (unit.code == 'repair'): R&M table and Excel matching the reference
  (Date Started, Date Completed, Name of Activity, Description, Requesting Office, Status,
   Total Materials, Labor, Total) with orange header in Excel.
- Electrical (unit.code == 'electrical'): Electrical Services Unit table — Date Started, Date Complete,
  Name of Project, Description, Requesting Office, Assigned Personnel, Status, Material Cost, Labor Cost, Total Cost;
  orange header in Excel.
- Other units: use generic until structure is defined.
"""

# Key for table config: 'generic', 'repair', 'electrical'
WAR_TABLE_CONFIGS = {
    'generic': {
        'label': 'All units',
        'web_headers': [
            ('request_id', 'Request ID'),
            ('unit', 'Unit'),
            ('personnel', 'Personnel'),
            ('period_start', 'Period start'),
            ('period_end', 'Period end'),
            ('summary', 'Summary'),
            ('accomplishments', 'Accomplishments'),
            ('success_indicators', 'Success indicators'),
        ],
        'excel_headers': [
            'Request ID',
            'Unit',
            'Personnel',
            'Date Started',
            'Date Completed',
            'Name of Activity',
            'Description',
            'Requesting Office',
            'Status',
            'Total Materials',
            'Labor',
            'Total (Materials + Labor)',
        ],
        'header_fill': None,
        'excel_column_count': 12,
    },
    'repair': {
        'label': 'Repair and Maintenance',
        'web_headers': [
            ('date_started', 'Date Started'),
            ('date_completed', 'Date Completed'),
            ('name_of_activity', 'Name of Activity'),
            ('description', 'Description'),
            ('requesting_office', 'Requesting Office'),
            ('status', 'Status'),
            ('total_materials', 'Total Materials'),
            ('labor', 'Labor'),
            ('total', 'Total (Materials + Labor)'),
        ],
        'excel_headers': [
            'Date Started',
            'Date Completed',
            'Name of Activity',
            'Description',
            'Requesting Office',
            'Status',
            'Total Materials',
            'Labor',
            'Total (Materials + Labor)',
        ],
        'header_fill': 'FFA500',  # Orange for R&M (reference)
        'excel_column_count': 9,
    },
    'electrical': {
        'label': 'Electrical Services Unit',
        'web_headers': [
            ('date_started', 'Date Started'),
            ('date_complete', 'Date Complete'),
            ('name_of_project', 'Name of Project'),
            ('description', 'Description'),
            ('requesting_office', 'Requesting Office'),
            ('assigned_personnel', 'Assigned Personnel'),
            ('status', 'Status'),
            ('material_cost', 'Material Cost'),
            ('labor_cost', 'Labor Cost'),
            ('total_cost', 'Total Cost'),
        ],
        'excel_headers': [
            'Date Started',
            'Date Complete',
            'Name of Project',
            'Description',
            'Requesting Office',
            'Assigned Personnel',
            'Status',
            'Material Cost',
            'Labor Cost',
            'Total Cost',
        ],
        'header_fill': 'FFA500',  # Orange (same as reference)
        'excel_column_count': 10,
    },
}


def get_war_table_config(unit):
    """
    Return table config key and config dict for the given unit.
    - unit is None -> 'generic'
    - unit.code == 'repair' -> 'repair'
    - unit.code == 'electrical' -> 'electrical'
    - else -> 'generic'
    """
    if unit is None:
        return 'generic', WAR_TABLE_CONFIGS['generic']
    code = (getattr(unit, 'code', None) or '').strip().lower()
    if code == 'repair':
        return 'repair', WAR_TABLE_CONFIGS['repair']
    if code == 'electrical':
        return 'electrical', WAR_TABLE_CONFIGS['electrical']
    return 'generic', WAR_TABLE_CONFIGS['generic']
