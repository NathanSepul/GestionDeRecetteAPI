from rest_framework import viewsets, status,permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from django.db import transaction
from django.db.models import Max
from gestionDeRecette.api_views import IsOwner
from typeRecette.models import TypeRecette
from typeRecette.serializer import TypeRecetteSerializer, ReorderTypeRecetteSerializer

@extend_schema(tags=['Type de recette'])
class TypeRecetteViewSet(viewsets.ModelViewSet):
    queryset = TypeRecette.objects.all()
    serializer_class = TypeRecetteSerializer
    pagination_class = None
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    
    def get_queryset(self):
        """
        Return the list of type recette
        """
        queryset = super().get_queryset()
        
        # queryset = queryset.filter(user_id=self.request.user.id)
        userID = self.request.GET.get('userId')
        if userID:
            queryset = queryset.filter(user_id=userID)
        
        return queryset.order_by('noOrdre')
    
    def perform_create(self, serializer):
        """Assigne automatiquement l'utilisateur lors de la création."""
        max_no_ordre = TypeRecette.objects.filter(  user=self.request.user ).aggregate(Max('noOrdre'))['noOrdre__max']
        next_no_ordre = (max_no_ordre if max_no_ordre is not None else -1) + 1
        serializer.save(user=self.request.user, noOrdre=next_no_ordre)

    @action(detail=True, methods=['post'], serializer_class=ReorderTypeRecetteSerializer)
    def reorder(self, request, pk=None):
        """Triage de l'ordre des types de recettes."""
        try:
            serializer = self.serializer_class(data=request.data)
            serializer.is_valid(raise_exception=True)
            new_position = serializer.validated_data["newPosition"]

            with transaction.atomic():
                type_to_move = self.get_object()
                type_to_reorder = TypeRecette.objects.filter(user_id=self.request.user.id).exclude(id=type_to_move.id).order_by('noOrdre')

                new_ordered_list = []

                if new_position == 0:
                    new_ordered_list.append(type_to_move)

                for i, type in enumerate(type_to_reorder):
                    new_ordered_list.append(type)
                    if i + 1 == new_position:
                        new_ordered_list.append(type_to_move)

                for index, type in enumerate(new_ordered_list):
                    type.noOrdre = index
                    type.save()
                    
            serializer =  TypeRecetteSerializer(new_ordered_list, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"detail": f"Une erreur s'est produite lors de la réorganisation : {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 