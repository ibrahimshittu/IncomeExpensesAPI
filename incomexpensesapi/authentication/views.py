from django.shortcuts import render
from rest_framework import generics, status, views, permissions
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from .serializers import registerSerializer, emailVerificationSerializer, loginSerializer, RequestPasswordResetSerializer, SetNewPasswordSerializer, LogoutSerializer
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User
from .utils import Util
from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import jwt
from .renderers import UserRenderer
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import smart_str, smart_bytes, DjangoUnicodeDecodeError
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode

# Create your views here.


class registerView(generics.GenericAPIView):

    serializer_class = registerSerializer
    renderer_classes = (UserRenderer,)

    def post(self, request):
        user = request.data
        serializer = self.serializer_class(data=user)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        user_data = serializer.data

        model_user = User.objects.get(email=user_data['email'])

        token = RefreshToken.for_user(model_user).access_token

        current_site = get_current_site(request).domain
        relativeLink = reverse("verify-email")

        absurl = 'http://' + current_site + \
            relativeLink + "?token=" + str(token)

        email_body = "Hi, " + model_user.username + \
            " Use the link below to verify your email address: \n" + absurl

        data = {
            "to_email": model_user.email, "email_body": email_body, "email_subject": "Verify Your Account"
        }
        Util.send_mail(data)

        return Response({"details": user_data, "message": "chill!, check your email to activate your account"}, status=status.HTTP_201_CREATED)


class VerifyEmail(views.APIView):
    serializer_class = emailVerificationSerializer
    token_param_config = openapi.Parameter(
        "token", in_=openapi.IN_QUERY, type=openapi.TYPE_STRING, description="")

    @swagger_auto_schema(manual_parameters=[token_param_config])
    def get(self, request):
        token = request.GET.get('token')

        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms="HS256")
            user = User.objects.get(id=payload["user_id"])
            # print(user)

            if not user.is_verified:
                user.is_verified = True
                user.save()
            return Response("Congrats fam!, Email activated successfully", status.HTTP_200_OK)

        except jwt.ExpiredSignatureError as e:
            return Response("Activation expired, refresh!", status.HTTP_400_BAD_REQUEST)

        except jwt.exceptions.DecodeError as e:
            return Response({"Invalid Token, refresh!"}, status.HTTP_400_BAD_REQUEST)


class loginview(generics.GenericAPIView):
    serializer_class = loginSerializer

    def post(self, request):
        user = request.data
        serializer = self.serializer_class(data=user)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.data, status.HTTP_200_OK)


class RequestPasswordReset(generics.GenericAPIView):
    serializer_class = RequestPasswordResetSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        email = request.data.get('email', '')

        if User.objects.filter(email=email).exists():
            user = User.objects.get(email=email)

            uidb64 = urlsafe_base64_encode(smart_bytes(user.id))
            token = PasswordResetTokenGenerator().make_token(user)
            current_site = get_current_site(request=request).domain
            relativeLink = reverse("password_reset_check", kwargs={
                "uidb64": uidb64, "token": token})

            absurl = 'http://' + current_site + relativeLink

            email_body = "Hi, " + user.username + \
                " Use the link below to reset your password: \n" + absurl

            data = {
                "to_email": user.email, "email_body": email_body, "email_subject": "Reset Your Password"
            }
            Util.send_mail(data)
        return Response({"success": "You have been sent a password reset email"}, status.HTTP_200_OK)


class PasswordTokenCheckAPIView(generics.GenericAPIView):
    def get(self, request, uidb64, token):

        try:
            user_id = smart_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(id=user_id)

            if not PasswordResetTokenGenerator().check_token(user, token):
                return Response({'error': 'Token is invalid, request new one'}, status.HTTP_401_UNAUTHORIZED)

            return Response({'success': True, 'message': 'credentials is valid', 'uidb64': uidb64, 'token': token}, status.HTTP_200_OK)
        except DjangoUnicodeDecodeError:
            return Response({'error': 'Token is invalid, request new one'}, status.HTTP_401_UNAUTHORIZED)


class SetNewPassword(generics.GenericAPIView):
    serializer_class = SetNewPasswordSerializer

    def patch(self, request):
        serializer = self.serializer_class(data=request.data)

        serializer.is_valid(raise_exception=True)
        return Response({'success': True, 'message': 'Password Reset Successful'}, status.HTTP_200_OK)


class LogoutView(generics.GenericAPIView):
    serializer_class = LogoutSerializer

    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid()
        serializer.save()
        return Response({'success': True, 'message': 'Logout Successful'}, status.HTTP_204_NO_CONTENT)
