import { Injectable } from '@angular/core';

/**
 * Guarda en memoria el estado de los formularios para que no se pierda
 * lo escrito al cambiar de modulo y volver.
 *
 * Es un singleton (providedIn: 'root'), asi que NO se destruye al navegar
 * entre paginas (a diferencia de los componentes). Cada formulario guarda
 * su estado al destruirse (ngOnDestroy) y lo restaura al crearse.
 *
 * Nota: el estado vive solo en memoria; se limpia al recargar la pagina (F5)
 * o cerrar la pestania. Es el comportamiento esperado.
 */
@Injectable({ providedIn: 'root' })
export class FormState {
  private store = new Map<string, unknown>();

  /** Guarda (o reemplaza) el estado de un formulario. */
  save(key: string, value: unknown): void {
    this.store.set(key, value);
  }

  /** Devuelve el estado guardado de un formulario, o undefined si no hay. */
  load<T>(key: string): T | undefined {
    return this.store.get(key) as T | undefined;
  }
}
