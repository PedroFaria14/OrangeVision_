from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError

from ..application.errors import ApplicationError

MAX_UPLOAD_BYTES = 5 * 1024 * 1024


class SampleImages:
    def normalize(self, content):
        if not content or len(content) > MAX_UPLOAD_BYTES:
            raise ApplicationError(413, 'Envie uma imagem de até 5 MiB.')
        try:
            with Image.open(BytesIO(content)) as source:
                if (
                    source.format not in ('JPEG', 'PNG', 'WEBP')
                    or getattr(source, 'n_frames', 1) != 1
                ):
                    raise ApplicationError(422, 'Use uma imagem estática JPEG, PNG ou WebP.')
                if source.width * source.height > 16000000:
                    raise ApplicationError(422, 'Imagem acima do limite de 16 milhões de pixels.')
                source.load()
                oriented = ImageOps.exif_transpose(source)
                oriented.thumbnail((1600, 1600))
                image = oriented.convert('RGBA')
                background = Image.new('RGBA', image.size, 'white')
                image = Image.alpha_composite(background, image).convert('RGB')
                output = BytesIO()
                image.save(output, format='JPEG', quality=90)
                return output.getvalue(), image.width, image.height
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
            raise ApplicationError(422, 'O arquivo não é uma imagem suportada e legível.') from exc

    def mask(self, content, width, height):
        if len(content) > 1500000:
            raise ApplicationError(413, 'Máscara acima do limite.')
        try:
            with Image.open(BytesIO(content)) as image:
                if image.format != 'PNG' or image.size != (width, height) or image.mode != 'L':
                    raise ApplicationError(
                        422, 'Máscara exige PNG em tons de cinza nas dimensões da amostra.'
                    )
                image.load()
                if any(
                    value not in (0, 255) for value, count in enumerate(image.histogram()) if count
                ):
                    raise ApplicationError(422, 'Máscara deve ser binária.')
                output = BytesIO()
                image.save(output, format='PNG')
                return output.getvalue()
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
            raise ApplicationError(422, 'Máscara inválida.') from exc
