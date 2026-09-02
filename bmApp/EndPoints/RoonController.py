# for andPoints that working with rooms
from rest_framework.response import Response # type: ignore
from rest_framework.decorators import api_view # type: ignore
from ..serializers import *
from ..models import *
import os
from django.conf import settings
import uuid

@api_view(['POST'])
def uploadRoomPhotos(request, room_id):
    try:
        room = RoomEntity.objects.get(id=room_id)
    except RoomEntity.DoesNotExist:
        return Response({'error': 'Room not found'}, status=404)
    
    if 'file' not in request.FILES:
        return Response({'error': 'No file provided'}, status=400)
    
    file = request.FILES['file']
    
    photo_dir = f'rooms/{room_id}/'
    photo_dir_path = os.path.join(settings.MEDIA_ROOT, photo_dir)
    
    os.makedirs(photo_dir_path, exist_ok=True)
    
    file_name, file_ext = os.path.splitext(file.name)
    unique_filename = f'{file_name}_{uuid.uuid4().hex[:8]}{file_ext}'
    
    file_path = os.path.join(photo_dir_path, unique_filename)
    with open(file_path, 'wb+') as destination:
        for chunk in file.chunks():
            destination.write(chunk)
    room.photo = photo_dir
    room.save()
    
    return Response({'message': 'Photo uploaded successfully', 'photo_url': f'{settings.MEDIA_URL}{photo_dir}{unique_filename}'}, status=201)

@api_view(['GET'])
def getRoomPhotos(request, room_id):
    try:
        room = RoomEntity.objects.get(id=room_id)
    except RoomEntity.DoesNotExist:
        return Response({'error': 'Room not found'}, status=404)
    
    if not room.photo:
        return Response({'photos': []}, status=200)
    
    photo_dir_path = os.path.join(settings.MEDIA_ROOT, room.photo)
    
    if not os.path.exists(photo_dir_path):
        return Response({'photos': []}, status=200)
    
    photos = []
    try:
        for filename in os.listdir(photo_dir_path):
            file_path = os.path.join(photo_dir_path, filename)
            if os.path.isfile(file_path):
                photo_url = f'{settings.MEDIA_URL}{room.photo}{filename}'
                photos.append({'photo': photo_url})
    except Exception as e:
        return Response({'error': f'Error reading photos: {str(e)}'}, status=500)
    
    return Response({'photos': photos}, status=200)