"""Pareamento pela janela; nunca solicita senha/cookie do usuário ao dispositivo."""

import webbrowser

from .camera_review import CaptureNotAuthorized
from .config import effective_values
from .worker import ClockFailure, validate_grant


def ask_connection_code(worker):
    try:
        import tkinter as tk
        from tkinter import messagebox, simpledialog
    except ImportError as exc:
        raise CaptureNotAuthorized(
            'A conexão pela janela exige Tkinter. Use o pareamento pelo terminal neste equipamento.'
        ) from exc
    root = tk.Tk()
    root.withdraw()
    try:
        grant = worker.store.active_grant()
        if grant:
            try:
                expiry = validate_grant(grant, worker.device_id)
            except ClockFailure as exc:
                raise CaptureNotAuthorized(str(exc)) from exc
            except (RuntimeError, ValueError, KeyError, TypeError):
                pass
            else:
                messagebox.showinfo(
                    'Equipamento já pareado',
                    f'Operador: {grant["operator_name"]}\n'
                    f'Sessão: {grant["id"]}\n'
                    f'Autorização local válida até '
                    f'{expiry.astimezone():%d/%m/%Y %H:%M %Z}.\n\n'
                    'Não é necessário informar outro código.\n'
                    'Pareado não comprova conexão com o servidor nem câmera disponível.\n'
                    'Para trocar de sessão, encerre a sessão local primeiro.',
                    parent=root,
                )
                return None
        if worker.store.pairing_attempt():
            if messagebox.askyesno(
                'Pareamento pendente',
                'Existe uma tentativa de pareamento não confirmada.\n'
                'Deseja retomá-la sem informar outro código?',
                parent=root,
            ):
                return None, False
            return None
        frontend = (effective_values().get('WEB_FRONTEND_ORIGIN') or 'http://127.0.0.1:5174').rstrip('/')
        webbrowser.open(frontend + '/dashboard/inspecoes')
        code = simpledialog.askstring(
            'Conectar sessão OrangeVision',
            'Na página Inspeções, inicie uma nova sessão para este equipamento.\nCopie o código temporário e cole abaixo.\nNão informe senha, credencial ou ID do equipamento.',
            parent=root,
            show='*',
        )
        if not code:
            return None
        code = code.strip()
        if not 32 <= len(code) <= 128:
            raise CaptureNotAuthorized('Cole o código temporário completo emitido pelo site.')
        pending = worker.store.pairing_attempt()
        cancel = False
        if pending and pending['pairing_code'] != code:
            cancel = messagebox.askyesno(
                'Tentativa anterior pendente',
                'Existe uma tentativa salva. Reconciliar seu encerramento antes de usar o novo código?',
                parent=root,
            )
            if not cancel:
                return None
        return code, cancel
    finally:
        root.destroy()
