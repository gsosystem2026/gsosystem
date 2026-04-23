"""Forms for inventory CRUD and adjust quantity (Phase 3.2 / 3.3)."""
from django import forms
from .models import InventoryItem, InventoryTransaction
from .models import format_quantity_with_uom


CATEGORY_CHOICES = [
    ('Supplies', 'Supplies'),
    ('Tools', 'Tools'),
    ('Electrical', 'Electrical'),
    ('Plumbing', 'Plumbing'),
    ('Cleaning', 'Cleaning'),
    ('Furniture', 'Furniture'),
]

UNIT_OF_MEASURE_CHOICES = [
    ('pcs', 'Pieces (pcs)'),
    ('box', 'Box'),
    ('set', 'Set'),
    ('roll', 'Roll'),
    ('liters', 'Liters'),
    ('meters', 'Meters'),
]


class InventoryItemForm(forms.ModelForm):
    """Unit Head: unit is set in view; no unit field."""
    class Meta:
        model = InventoryItem
        fields = [
            'name', 'description', 'category', 'quantity', 'unit_of_measure',
            'reorder_level', 'arrival_date', 'location', 'serial_or_asset_number',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Item name'}),
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Description (optional)'}),
            'arrival_date': forms.DateInput(attrs={'type': 'date'}),
            'location': forms.TextInput(attrs={'placeholder': 'Storage location or remarks'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Category as dropdown with sample options (optional field)
        self.fields['category'] = forms.ChoiceField(
            choices=[('', 'Select category (optional)')] + CATEGORY_CHOICES,
            required=False,
        )
        # Unit of measure as dropdown with common units (optional, defaults handled by model)
        self.fields['unit_of_measure'] = forms.ChoiceField(
            choices=[('', 'Select UoM (optional)')] + UNIT_OF_MEASURE_CHOICES,
            required=False,
            label='Unit of Measure (UoM)',
            help_text='Examples: pcs, liters, box, set',
        )


class InventoryItemFormAllUnits(InventoryItemForm):
    """GSO Office / Director: include unit choice."""
    class Meta(InventoryItemForm.Meta):
        fields = [
            'unit', 'name', 'description', 'category', 'quantity', 'unit_of_measure',
            'reorder_level', 'arrival_date', 'location', 'serial_or_asset_number',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.gso_units.models import Unit
        self.fields['unit'].queryset = Unit.objects.filter(is_active=True).order_by('name')
        self.fields['unit'].required = True
        self.fields['unit'].label = 'Department'
        self.fields['unit'].help_text = 'Choose the service unit/department (e.g., Electrical, Utility, Motorpool)'


class InventoryAdjustForm(forms.Form):
    TRANSACTION_TYPE = [
        ('IN', 'Stock In'),
        ('OUT', 'Stock Out'),
    ]
    transaction_type = forms.ChoiceField(choices=TRANSACTION_TYPE, widget=forms.RadioSelect)
    quantity = forms.IntegerField(min_value=1, widget=forms.NumberInput(attrs={'min': 1}))
    arrival_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    supplier_name = forms.CharField(
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs={'placeholder': 'Optional supplier'}),
    )
    delivery_reference = forms.CharField(
        required=False,
        max_length=120,
        widget=forms.TextInput(attrs={'placeholder': 'Optional DR/PO ref'}),
    )
    notes = forms.CharField(required=False, max_length=500, widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'Optional notes'}))

    def clean_quantity(self):
        qty = self.cleaned_data.get('quantity')
        if qty is not None and qty < 1:
            raise forms.ValidationError('Quantity must be at least 1.')
        return qty

    def clean(self):
        cleaned = super().clean()
        trans_type = cleaned.get('transaction_type')
        if trans_type == 'IN' and not cleaned.get('arrival_date'):
            self.add_error('arrival_date', 'Arrival date is required for stock-in entries.')
        return cleaned


class IssueMaterialForm(forms.Form):
    """Unit Head: issue material from inventory to a request (deducts stock)."""
    item = forms.ModelChoiceField(
        queryset=InventoryItem.objects.none(),
        required=True,
        label='Item',
        help_text='Item from your unit inventory',
        widget=forms.Select(attrs={'class': 'js-issue-material-select'}),
    )
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'min': 1, 'placeholder': 'Qty'}),
        label='Quantity',
    )
    notes = forms.CharField(
        required=False,
        max_length=500,
        widget=forms.TextInput(attrs={'placeholder': 'Optional notes'}),
    )

    def __init__(self, *args, unit_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        if unit_id is not None:
            self.fields['item'].queryset = (
                InventoryItem.objects.filter(unit_id=unit_id, quantity__gt=0)
                .select_related('unit')
                .order_by('name')
            )

    def clean_quantity(self):
        qty = self.cleaned_data.get('quantity')
        item = self.cleaned_data.get('item')
        if qty is not None and item and qty > item.quantity:
            raise forms.ValidationError(
                f'Not enough stock. Available: {format_quantity_with_uom(item.quantity, item.unit_of_measure)}.'
            )
        return qty


class RequestMaterialForm(forms.Form):
    """Personnel: request material for a request; Unit Head approval required before deduction."""
    item = forms.ModelChoiceField(
        queryset=InventoryItem.objects.none(),
        required=True,
        label='Item',
        help_text='Item from unit inventory',
        widget=forms.Select(attrs={'class': 'js-request-material-select'}),
    )
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'min': 1, 'placeholder': 'Qty'}),
        label='Quantity',
    )
    notes = forms.CharField(
        required=False,
        max_length=500,
        widget=forms.TextInput(attrs={'placeholder': 'Optional notes (e.g. purpose)'}),
    )

    def __init__(self, *args, unit_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        if unit_id is not None:
            self.fields['item'].queryset = (
                InventoryItem.objects.filter(unit_id=unit_id, quantity__gt=0)
                .select_related('unit')
                .order_by('name')
            )

    def clean_quantity(self):
        qty = self.cleaned_data.get('quantity')
        item = self.cleaned_data.get('item')
        if qty is not None and item and qty > item.quantity:
            raise forms.ValidationError(
                f'Not enough stock. Available: {format_quantity_with_uom(item.quantity, item.unit_of_measure)}.'
            )
        return qty
