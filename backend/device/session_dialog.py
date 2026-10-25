"""Pareamento pela janela; nunca solicita senha/cookie do usuário ao dispositivo."""

import os
import webbrowser

from .camera_review import CaptureNotAuthorized


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
        frontend = os.getenv('WEB_FRONTEND_ORIGIN', 'http://127.0.0.1:5174').rstrip('/')
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
