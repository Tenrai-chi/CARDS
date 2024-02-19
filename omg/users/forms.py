from PIL import Image
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import Profile, Guild, GuildBuff


class LoginForm(AuthenticationForm):
    """ Форма авторизации.
    """

    username = forms.CharField(max_length=150,
                               label='Имя пользователя',
                               widget=forms.TextInput(attrs={
                                   'class': 'form-control',
                                   'placeholder': 'Введите имя пользователя'})
                               )
    password = forms.CharField(max_length=128,
                               label='Пароль',
                               widget=forms.PasswordInput(attrs={
                                   'class': 'form-control',
                                   'placeholder': 'Введите пароль'})
                               )

    class Meta:
        model = User
        fields = ['username', 'password']


class RegistrationForm(UserCreationForm):
    """ Форма регистрации.
    """

    username = forms.CharField(max_length=150,
                               label='Имя пользователя',
                               widget=forms.TextInput(attrs={'class': 'form-control',
                                                             'placeholder': 'Введите имя пользователя'}))

    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control',
                                                            'placeholder': 'Введите email'})
                             )
    password1 = forms.CharField(max_length=128,
                                label='Пароль',
                                widget=forms.PasswordInput(attrs={'class': 'form-control',
                                                                  'placeholder': 'Введите пароль'})
                                )
    password2 = forms.CharField(max_length=128,
                                label='Подтверждение пароля',
                                widget=forms.PasswordInput(attrs={'class': 'form-control',
                                                                  'placeholder': 'Повторите пароль'})
                                )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', ]


class EditProfileForm(forms.ModelForm):
    """ Форма редактирования профиля.
    """

    about_user = forms.CharField(label='Обо мне:', widget=forms.Textarea)
    profile_pic = forms.ImageField(label='Аватарка')

    class Meta:
        model = Profile
        fields = ['about_user', 'profile_pic']


class EditGuildInfoForm(forms.ModelForm):
    """ Форма редактирования информации о гильдии.
    """

    name = forms.CharField(label='Название')
    guild_pic = forms.ImageField(label='Аватарка')
    buff = forms.ModelChoiceField(queryset=GuildBuff.objects.all(),
                                  label='Усиление',
                                  empty_label='---------------',
                                  )

    class Meta:
        model = Guild
        fields = ['name', 'guild_pic', 'buff']


class CreateGuildForm(forms.ModelForm):
    """ Форма создания гильдии.
    """

    name = forms.CharField(label='Название')
    guild_pic = forms.ImageField(label='Аватарка')
    buff = forms.ModelChoiceField(queryset=GuildBuff.objects.all(),
                                  label='Усиление',
                                  empty_label='---------------',
                                  )

    class Meta:
        model = Guild
        fields = ['name', 'guild_pic', 'buff']
