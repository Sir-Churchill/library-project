from rest_framework import generics

from users.serializers import UserSerializer


class CreateUserView(generics.CreateAPIView):
    serializer_class = UserSerializer
    authentication_classes = ()
    permission_classes = ()


class ManageUserView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    authentication_classes = ()
    permission_classes = ()

    def get_object(self):
        return self.request.user
