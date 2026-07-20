import math
from rest_framework import pagination
from rest_framework.response import Response
from django.core.paginator import EmptyPage

class MyPagination(pagination.PageNumberPagination):
    page_size_query_param = 'pageSize'
    
    def get_paginated_response(self, data):
        
        return Response({
            'next': self.page.has_next(),
            'previous': self.page.has_previous(),
            'current': self.page.number,
            'count': len(data) - 1,
            'nbrTotalResult': self.page.paginator.count,
            'results': data
        })
    
    def paginate_queryset(self, queryset, request, view=None):
        self.page_size = self.get_page_size(request)
        if not self.page_size:
            return None

        page_number = request.query_params.get('page', '1')

        if not isinstance(page_number, str) or not page_number.isdigit() or int(page_number) <= 0:
            page_number = '1'

        request.query_params._mutable = True
        request.query_params['page'] = page_number
        request.query_params._mutable = False

        try:
            return super().paginate_queryset(queryset, request, view)
        except EmptyPage:
            last_page = self.django_paginator.num_pages
            
            request.query_params._mutable = True
            request.query_params['page'] = str(last_page if last_page > 0 else 1)
            request.query_params._mutable = False
            
            return super().paginate_queryset(queryset, request, view)