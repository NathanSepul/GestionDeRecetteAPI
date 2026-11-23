from django.core.mail import send_mail
from django.template.loader import render_to_string

from rest_framework import generics, mixins, permissions, viewsets, status, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.throttling import ScopedRateThrottle
from gestionDeRecette.api_views import IsOwner
from rest_framework_simplejwt.tokens import RefreshToken

from rest_registration.api.views.reset_password import process_reset_password_data, ResetPasswordSerializer, send_reset_password_link
from rest_registration.utils.responses import get_ok_response
from rest_registration.settings import registration_settings

from drf_spectacular.utils import extend_schema

from .models import User
from .serializer import UserSerializer, LanguageSerializers, UserBaseSerializer

@extend_schema(tags=['Utilisateur'])
class UserViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """
    Gestion centralisée des profils utilisateurs :
    Lecture, Mise à jour, Langue, Follow et Unregister.
    Ni création (comptes créés dans l'admin) ni suppression (unregister désactive le compte sans effacer ses recettes).
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    filter_backends = [filters.SearchFilter]
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    search_fields = ['email', 'first_name', 'last_name']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return UserBaseSerializer
        return UserSerializer

    # Action pour gérer la langue (GET pour lire, PUT pour modifier)
    @action(detail=True, methods=['get', 'put'], serializer_class=LanguageSerializers)
    def language(self, request, pk=None):
        user = self.get_object()
        if request.method == 'PUT':
            serializer = LanguageSerializers(user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        return Response(LanguageSerializers(user).data)

    # Action pour S'abonner / Se désabonner
    # IsOwner bloquerait le POST sur le profil d'un autre : suivre quelqu'un ne modifie que request.user
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def follow(self, request, pk=None):
        user_to_follow = self.get_object()
        me = request.user
        
        if me == user_to_follow:
            return Response({"error": "Auto-follow forbidden"}, status=status.HTTP_400_BAD_REQUEST)
            
        if me.following.filter(id=user_to_follow.id).exists():
            me.following.remove(user_to_follow)
            return Response({"is_followed": False}, status=status.HTTP_200_OK)
        
        me.following.add(user_to_follow)
        return Response({"is_followed": True}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], serializer_class=UserBaseSerializer)
    def following_list(self, request, pk=None):
        user = self.get_object()
        following = user.following.all()
        serializer = UserBaseSerializer(following, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['put'], url_path='unregister', permission_classes=[permissions.IsAuthenticated])
    def unregister(self, request):
        user = request.user
        user.is_active = False
        user.save()

        # Envoi de l'email
        subject = render_to_string('email/unregistration/subject.txt')
        body = render_to_string('email/unregistration/body.txt')
        send_mail(subject, body, None, [user.email], fail_silently=False)

        return Response({'message': 'Profile successfully disabled.'})


# MOT DE PASSE (pas d'inscription libre : les comptes sont créés dans l'admin Django)

@extend_schema(tags=['Utilisateur'])
class SendResetPasswordLinkView(generics.GenericAPIView):
    serializer_class = registration_settings.SEND_RESET_PASSWORD_LINK_SERIALIZER_CLASS
    permission_classes = [permissions.AllowAny]
    # ouvert à tous et envoie un email : limité pour éviter de bombarder une boîte mail
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'reset_password'
    def post(self, request, *args, **kwargs):
        return send_reset_password_link(request._request)

@extend_schema(tags=['Utilisateur'])
class ResetPasswordView(generics.GenericAPIView):
    serializer_class = ResetPasswordSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'reset_password'
    def post(self, request, *args, **kwargs):
        process_reset_password_data(request.data, serializer_context={'request': request})
        user = User.objects.get(id=request.data['user_id'])
        refresh = RefreshToken.for_user(user)
        return get_ok_response({
            "user_id": str(user.id),
            "refresh": str(refresh),
            "access": str(refresh.access_token)
        })