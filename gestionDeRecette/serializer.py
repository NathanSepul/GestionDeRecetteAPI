
from rest_framework import pagination
from rest_framework.response import Response
from django.shortcuts import redirect
from rest_framework.pagination import CursorPagination
from django.http import QueryDict
import math

class MyPagination(pagination.PageNumberPagination):

    page_size_query_param = 'pageSize'
    
    def get_paginated_response(self, data):
        return Response({
            'next': self.page.has_next(),
            'previous': self.page.has_previous(),
            'current': self.page.number,
            'count': self.page.paginator.count - 1,
            'results': data})
    
    def paginate_queryset(self, queryset, request, view=None):
        
        page_number = request.query_params.get('page',1)

        # Vérification que page_number est une chaîne de caractères
        if not isinstance(page_number, str):
            page_number=1

        # Vérification que page_number est un nombre entier valide
        elif not page_number.isdigit() or int(page_number) <= 0:
            page_number=1

        last_page = math.ceil(queryset.count() / self.page_size) 
        
        if last_page != 0 and int(page_number) > last_page:
            page_number = last_page

        request.query_params._mutable = True
        request.query_params['page'] = page_number
        request.query_params._mutable = False
        
        return super().paginate_queryset( queryset, request, view)
    
