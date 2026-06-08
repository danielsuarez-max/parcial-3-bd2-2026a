import { Injectable, signal } from '@angular/core';

/** Un toast (notificación flotante autodescartable). */
export interface ToastMsg {
  id: number;
  tipo: 'exito' | 'error';
  texto: string;
}

@Injectable({ providedIn: 'root' })
export class Toast {
  // Lista reactiva de toasts visibles; el componente app-toasts la pinta.
  mensajes = signal<ToastMsg[]>([]);
  private seq = 0;

  /** Muestra un toast de éxito (verde). */
  exito(texto: string): void { this.mostrar('exito', texto); }

  /** Muestra un toast de error (rojo). */
  error(texto: string): void { this.mostrar('error', texto); }

  private mostrar(tipo: 'exito' | 'error', texto: string): void {
    const id = ++this.seq;
    this.mensajes.update((lista) => [...lista, { id, tipo, texto }]);
    // Se descarta solo a los 4 segundos.
    setTimeout(() => this.cerrar(id), 4000);
  }

  /** Quita un toast (botón ✕ o al expirar). */
  cerrar(id: number): void {
    this.mensajes.update((lista) => lista.filter((m) => m.id !== id));
  }
}
