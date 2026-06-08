import { Component, signal, inject, HostListener } from '@angular/core';
import { FormsModule } from '@angular/forms';
import {
  Api, TipoVehiculoItem, EspacioLibre, EntradaIn, MensualidadActiva
} from '../../services/api';
import { Toast } from '../../services/toast';

@Component({
  selector: 'app-registrar-entrada',
  imports: [FormsModule],
  templateUrl: './registrar-entrada.html',
  styleUrl: './registrar-entrada.css'
})
export class RegistrarEntradaComponent {
  private api = inject(Api);
  private toast = inject(Toast);

  // --- Datos del formulario (enlazados con [(ngModel)]) ---
  placa = '';
  idTipo: number | null = null;
  idEspacio: number | null = null;
  color = '';
  marca = '';

  // --- Estado para llenar los dropdowns ---
  tipos = signal<TipoVehiculoItem[]>([]);
  espacios = signal<EspacioLibre[]>([]);   // libres del tipo elegido (solo ocasional)
  espaciosAbierto = signal(false);         // ¿está abierta la lista del dropdown de espacios?

  // --- Detección de mensualidad ---
  // null = aún no se consultó; true/false = resultado de la consulta.
  esMensual = signal<boolean | null>(null);
  mensual = signal<MensualidadActiva | null>(null);

  // --- Estado del envío ---
  enviando = signal(false);

  constructor() {
    // Llenamos el dropdown de tipos al abrir la vista.
    this.api.getTipos().subscribe({
      next: (resp) => this.tipos.set(resp.datos),
      error: (err) => { console.error(err); this.toast.error('No se pudieron cargar los tipos.'); }
    });
  }

  /** Al salir del campo placa: normaliza a mayúsculas y consulta si es mensual. */
  onPlacaBlur(): void {
    this.placa = this.placa.trim().toUpperCase();

    if (!this.placa) {
      this.esMensual.set(null);
      this.mensual.set(null);
      return;
    }

    this.api.getMensualidadDePlaca(this.placa).subscribe({
      next: (resp) => {
        if (resp.datos.length > 0) {
          // Es mensual: guardamos su cupo y ocultamos el selector de espacio.
          this.esMensual.set(true);
          this.mensual.set(resp.datos[0]);
        } else {
          // Es ocasional: habrá que elegir espacio según el tipo.
          this.esMensual.set(false);
          this.mensual.set(null);
          this.recargarEspacios();
        }
      },
      error: (err) => { console.error(err); this.toast.error('No se pudo verificar la mensualidad.'); }
    });
  }

  /** Al cambiar el tipo: si es ocasional, recarga los espacios libres compatibles. */
  onTipoChange(): void {
    this.idEspacio = null;
    this.espaciosAbierto.set(false);
    if (this.esMensual() === false) {
      this.recargarEspacios();
    }
  }

  private recargarEspacios(): void {
    if (this.idTipo === null) { this.espacios.set([]); return; }
    this.api.getEspaciosLibres(this.idTipo).subscribe({
      next: (resp) => this.espacios.set(resp.datos),
      error: (err) => { console.error(err); this.toast.error('No se pudieron cargar los espacios.'); }
    });
  }

  // ===== Dropdown personalizado de espacios =====
  // (Sustituye al <select> nativo, cuya lista emergente la dibuja el navegador
  //  y NO se puede limitar con CSS: por eso se salía de la pantalla.)

  /** Abre/cierra la lista. stopPropagation evita que este mismo clic llegue al
   *  document y dispare cerrarEspacios(), que la cerraría justo al abrirla. */
  toggleEspacios(ev: MouseEvent): void {
    ev.stopPropagation();
    this.espaciosAbierto.update(v => !v);
  }

  /** Elige un espacio y cierra la lista. */
  seleccionarEspacio(id: number): void {
    this.idEspacio = id;
    this.espaciosAbierto.set(false);
  }

  /** Texto del botón: el espacio elegido o el placeholder. */
  nombreEspacioElegido(): string {
    const e = this.espacios().find(x => x.id_espacio === this.idEspacio);
    return e ? `N° ${e.numero}` : '— Elige un espacio —';
  }

  /** Cierra la lista al hacer clic en cualquier parte del documento (clic fuera). */
  @HostListener('document:click')
  cerrarEspacios(): void {
    this.espaciosAbierto.set(false);
  }

  /** Cierra la lista con la tecla Escape. */
  @HostListener('document:keydown.escape')
  escEspacios(): void {
    this.espaciosAbierto.set(false);
  }

  /** Envía el POST /ingresos. */
  registrar(): void {
    if (!this.placa)        { this.toast.error('Escribe la placa.'); return; }
    if (this.idTipo === null) { this.toast.error('Elige el tipo de vehículo.'); return; }

    // Si es mensual, mandamos el cupo reservado (el backend lo usa igual).
    // Si es ocasional, mandamos el espacio seleccionado.
    let idEspacio: number | null;
    if (this.esMensual()) {
      idEspacio = this.mensual()!.id_espacio;
    } else {
      if (this.idEspacio === null) { this.toast.error('Elige un espacio.'); return; }
      idEspacio = this.idEspacio;
    }

    const entrada: EntradaIn = {
      placa: this.placa,
      id_tipo: this.idTipo,
      id_espacio: idEspacio,
      color: this.color || null,
      marca: this.marca || null,
    };

    this.enviando.set(true);
    this.api.postIngreso(entrada).subscribe({
      next: (resp) => {
        this.toast.exito(`${resp.mensaje}: placa ${resp.placa} (${resp.modalidad}) en el espacio N° ${resp.numero_espacio}.`);
        this.enviando.set(false);
        this.limpiar();
      },
      error: (err) => {
        this.toast.error(this.extraerError(err));
        this.enviando.set(false);
      }
    });
  }

  /** Limpia el formulario tras un registro exitoso. */
  private limpiar(): void {
    this.placa = '';
    this.idTipo = null;
    this.idEspacio = null;
    this.color = '';
    this.marca = '';
    this.espacios.set([]);
    this.espaciosAbierto.set(false);
    this.esMensual.set(null);
    this.mensual.set(null);
  }

  /**
   * Saca un mensaje legible del error HTTP.
   * FastAPI manda { detail: "texto" } o, en validaciones, { detail: [ {msg}, ... ] }.
   */
  private extraerError(err: any): string {
    const detail = err?.error?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) return detail.map((d) => d.msg).join(' · ');
    return 'No se pudo registrar la entrada.';
  }
}
