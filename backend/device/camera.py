class CameraFailure(Exception):
    pass


class Camera:
    def __init__(self, settings):
        if settings.width <= 0 or settings.height <= 0:
            raise CameraFailure('Defina resolução após medir câmera/iluminação reais.')
        self.settings, self.camera = settings, None

    def capture(self):
        if self.settings.camera_adapter == 'usb':
            import cv2

            if self.camera is None:
                self.camera = cv2.VideoCapture(self.settings.camera_index)
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.settings.width)
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.settings.height)
            if not self.camera.isOpened():
                raise CameraFailure('Câmera USB indisponível.')
            ok, frame = self.camera.read()
            if not ok:
                raise CameraFailure('Falha de aquisição; não foi produzida classificação.')
            return frame
        if self.settings.camera_adapter == 'csi':
            if self.camera is None:
                from picamera2 import Picamera2

                self.camera = Picamera2()
                # RGB888 do libcamera usa bytes BGR neste adaptador. Confirmar com carta de cor na bancada.
                self.camera.configure(
                    self.camera.create_still_configuration(
                        main={
                            'size': (self.settings.width, self.settings.height),
                            'format': 'RGB888',
                        }
                    )
                )
                self.camera.start()
            return self.camera.capture_array()
        raise CameraFailure(
            'Selecione explicitamente CAMERA_ADAPTER=usb ou csi após confirmar o hardware.'
        )

    def close(self):
        if self.camera is not None:
            camera, self.camera = self.camera, None
            if self.settings.camera_adapter == 'usb':
                camera.release()
            else:
                try:
                    camera.stop()
                finally:
                    camera.close()
