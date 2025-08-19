import user.models
from user.models import User
import user.serializer
from user.serializer import UserBaseSerializer

from django.core.mail import send_mail
from django.http import JsonResponse
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_registration import signals
from rest_registration.api.views.register import register as rest_register
from rest_registration.api.views.register import process_verify_registration_data, VerifyRegistrationSerializer
from rest_registration.api.views.reset_password import process_reset_password_data, ResetPasswordSerializer, send_reset_password_link as rest_send_reset_password_link
from rest_registration.utils.responses import get_ok_response
from rest_registration.settings import registration_settings
from rest_framework.views import APIView
from django.template.loader import render_to_string
from drf_spectacular.utils import extend_schema


@extend_schema(tags=['Utilisateur'])
class UserViewSet(generics.RetrieveAPIView):
    """
    Return an user by his id
    """

    queryset = user.models.User.objects.all()
    serializer_class = user.serializer.UserSerializer

    # @swagger_auto_schema(operation_id='Get user by id', security=[],)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

@extend_schema(tags=['Utilisateur'])
class UserViewUnregister(generics.UpdateAPIView):
    """
    Disable user's account
    """
    permission_classes = [permissions.IsAuthenticated,]
    http_method_names = ['put']
    
    queryset = user.models.User.objects.all()
    serializer_class = user.serializer.UserBaseSerializer

    # @swagger_auto_schema(operation_id='Unregister', security=[{"Bearer": []}],)
    def put(self, request, *args, **kwargs):
        queryset = super().get_queryset()
        user = queryset.get(pk = request.user.pk)
        user.is_active = False
        user.save()

        # Récupérer le contenu des fichiers texte
        subject = render_to_string('email/unregistration/subject.txt')
        body = render_to_string('email/unregistration/body.txt')

        send_mail(
            subject,
            body,
            None,
            [user.email],
            fail_silently=False,
        )
        message = 'Profile successfully disabled.'
        return Response({ message })


@extend_schema(tags=['Utilisateur'])
class UserViewSetUpdate(generics.UpdateAPIView):

    permission_classes = [permissions.IsAuthenticated,]
    http_method_names = ['put']
    
    queryset = user.models.User.objects.all()
    serializer_class = user.serializer.UserSerializer

    # @swagger_auto_schema(operation_id='Update user', security=[{"Bearer": []}],)
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

@extend_schema(tags=['Utilisateur'])
class LanguageViewSet(generics.RetrieveAPIView):
    """
    Return an user's language by his id
    """

    queryset = user.models.User.objects.all()
    serializer_class = user.serializer.LanguageSerializers

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

@extend_schema(tags=['Utilisateur'])
class UpdateLanguageView(generics.UpdateAPIView):
    """
    Update an language's user by his id
    """

    permission_classes = [permissions.IsAuthenticated,]
    http_method_names = ['put']
    
    queryset = user.models.User.objects.all()
    serializer_class = user.serializer.LanguageSerializers

    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

   

#
# Re ecriture des methodes de django rest registration pour avoir les access et refresh token et pour la documenation de l'api
#

@extend_schema(tags=['Utilisateur'])
class VerifyRegistrationView(generics.GenericAPIView):
    """
    Verify registration via signature.
    """

    serializer_class = VerifyRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        user = process_verify_registration_data(
        request.data, serializer_context={'request': request})

        signals.user_activated.send(sender=None, user=user, request=request)

        refresh = RefreshToken.for_user(user)

        data = {}
        data["user_id"] = str(user.id)
        data["refresh"] = str(refresh)
        data["access"] = str(refresh.access_token)

        return get_ok_response(data)


@extend_schema(tags=['Utilisateur'])
class RegisterView(generics.GenericAPIView):
    '''
    Saves the user's data and sends an email (with signature, timestamp and ID ) to verify his identity
    '''
    
    serializer_class = registration_settings.REGISTER_SERIALIZER_CLASS
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
       return rest_register(request._request)


@extend_schema(tags=['Utilisateur'])
class SendResetPasswordLinkView(generics.GenericAPIView):
    """
    Sends an email with a signature, timestamp, and ID to reset the password.
    """
    
    serializer_class = registration_settings.SEND_RESET_PASSWORD_LINK_SERIALIZER_CLASS
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        return rest_send_reset_password_link(request._request)
    

@extend_schema(tags=['Utilisateur'])
class ResetPasswordView(generics.GenericAPIView):
    '''
    Reset password, given the signature and timestamp from the link.
    '''
    
    serializer_class = ResetPasswordSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        process_reset_password_data( request.data, serializer_context={'request': request})

        user = User.objects.all().get(id=request.data['user_id'])
        refresh = RefreshToken.for_user(user)

        data = {}
        data["user_id"] = str(user.id)
        data["refresh"] = str(refresh)
        data["access"] = str(refresh.access_token)

        return get_ok_response(data)

    
    

