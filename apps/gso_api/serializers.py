"""
Serializers for GSO REST API.
"""
from rest_framework import serializers

from apps.gso_accounts.models import User
from apps.gso_requests.models import Request, RequestAssignment
from apps.gso_inventory.models import InventoryItem
from apps.gso_units.models import Unit
from apps.gso_notifications.models import Notification


class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unit
        fields = ['id', 'name', 'code', 'is_active']


class UserMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'role']


class UserMeSerializer(serializers.ModelSerializer):
    """Current user info for mobile app (id, username, role, unit_id, unit_name, can_approve)."""
    unit_id = serializers.IntegerField(allow_null=True)
    unit_name = serializers.SerializerMethodField()
    can_approve = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'role', 'unit_id', 'unit_name', 'can_approve']

    def get_unit_name(self, obj):
        return obj.unit.name if obj.unit_id else None

    def get_can_approve(self, obj):
        return getattr(obj, 'can_approve_requests', False)


class RequestListSerializer(serializers.ModelSerializer):
    display_id = serializers.ReadOnlyField()
    unit_name = serializers.ReadOnlyField()
    status_display = serializers.ReadOnlyField()
    requestor_name = serializers.SerializerMethodField()

    class Meta:
        model = Request
        fields = [
            'id', 'display_id', 'title', 'description', 'location',
            'unit', 'unit_name', 'requestor', 'requestor_name',
            'status', 'status_display', 'is_emergency',
            'labor', 'materials', 'others',
            'custom_full_name', 'custom_email', 'custom_contact_number',
            'created_at', 'updated_at',
        ]

    def get_requestor_name(self, obj):
        if obj.requestor_id:
            return obj.requestor.get_full_name() or obj.requestor.username
        return None


class RequestDetailSerializer(RequestListSerializer):
    assignments = serializers.SerializerMethodField()

    class Meta(RequestListSerializer.Meta):
        fields = RequestListSerializer.Meta.fields + ['assignments', 'attachment']

    def get_assignments(self, obj):
        return [
            {
                'personnel_id': a.personnel_id,
                'personnel_name': a.personnel.get_full_name() or a.personnel.username,
            }
            for a in obj.assignments.select_related('personnel').all()
        ]


class RequestCreateSerializer(serializers.ModelSerializer):
    """For external systems to submit a new request (creates as SUBMITTED)."""
    class Meta:
        model = Request
        fields = [
            'unit', 'title', 'description', 'location',
            'labor', 'materials', 'others',
            'custom_full_name', 'custom_email', 'custom_contact_number',
        ]

    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user if request else None
        if not user:
            raise serializers.ValidationError('Authentication required.')
        validated_data['requestor_id'] = user.id
        validated_data['status'] = Request.Status.SUBMITTED
        return super().create(validated_data)


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'link', 'read', 'created_at']


class InventoryItemSerializer(serializers.ModelSerializer):
    unit_name = serializers.CharField(source='unit.name', read_only=True)
    is_low_stock = serializers.ReadOnlyField()

    class Meta:
        model = InventoryItem
        fields = [
            'id', 'unit', 'unit_name', 'name', 'description', 'category',
            'quantity', 'unit_of_measure', 'reorder_level',
            'is_low_stock', 'location', 'serial_or_asset_number',
            'created_at', 'updated_at',
        ]
