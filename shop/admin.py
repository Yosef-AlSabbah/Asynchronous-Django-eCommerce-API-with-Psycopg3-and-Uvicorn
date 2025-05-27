from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import Category, Product, ProductStatus


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'product_count']
    list_display_links = ['name', 'slug']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}

    def product_count(self, obj):
        return obj.products.count()

    product_count.short_description = _('Products')


class ProductStatusInline(admin.TabularInline):
    model = ProductStatus
    extra = 0
    fields = ['status', 'reviewer', 'created_at', 'notes']
    readonly_fields = ['created_at']
    can_delete = False


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'thumbnail_preview', 'category', 'price', 'owner',
                    'approval_status', 'created_at']
    list_filter = ['category', 'created_at', 'owner']
    search_fields = ['name', 'short_description', 'owner__username']
    readonly_fields = ['created_at', 'updated_at', 'slug']
    list_display_links = ['name', 'thumbnail_preview']
    list_select_related = ['category', 'owner']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductStatusInline]

    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'category', 'price', 'owner')
        }),
        (_('Description'), {
            'fields': ('short_description',)
        }),
        (_('Image'), {
            'fields': ('thumbnail', 'thumbnail_preview')
        }),
        (_('Metadata'), {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at', 'tags')
        }),
    )

    def thumbnail_preview(self, obj):
        if obj.thumbnail:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover;" />',
                               obj.thumbnail.url)
        return '-'

    thumbnail_preview.short_description = _('Preview')

    def approval_status(self, obj):
        status = obj.current_approval
        if not status:
            return format_html('<span style="color: #999;">Not reviewed</span>')

        colors = {
            'pending': '#f39c12',
            'approved': '#27ae60',
            'rejected': '#e74c3c'
        }

        return format_html('<span style="color: {};">{}</span>',
                           colors.get(status.status, '#000'),
                           status.get_status_display())

    approval_status.short_description = _('Status')


@admin.register(ProductStatus)
class ProductStatusAdmin(admin.ModelAdmin):
    list_display = ['product', 'status', 'reviewer', 'created_at']
    list_filter = ['status', 'reviewer', 'created_at']
    search_fields = ['product__name', 'notes', 'reviewer__username']
    readonly_fields = ['created_at']
    raw_id_fields = ['product', 'reviewer']
    date_hierarchy = 'created_at'