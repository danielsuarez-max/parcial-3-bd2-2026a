import { Component, signal, inject, HostListener, OnDestroy } from '@angular/core';
import { FormsModule } from '@angular/forms';
import {
  Api, TipoVehiculoItem, EspacioLibre, EntradaIn, MensualidadActiva, Ocupacion, VehiculoInfo
} from '../../services/api';
import { Toast } from '../../services/toast';
import { FormState } from '../../services/form-state';

/** Lo que se conserva del formulario de entrada al cambiar de modulo. */
interface EstadoEntrada {
  placa: string;
  idTipo: number | null;
  idEspacio: number | null;
  color: string;
  marca: string;
  esMensual: boolean | null;
  mensual: MensualidadActiva | null;
  vehiculo: VehiculoInfo | null;
  vehiculoConocido: boolean;
}

@Component({
  selector: 'app-registrar-entrada',
  imports: [FormsModule],
  templateUrl: './registrar-entrada.html',
  styleUrl: './registrar-entrada.css'
})
export class RegistrarEntradaComponent implements OnDestroy {
  private api = inject(Api);
  private toast = inject(Toast);
  private formState = inject(FormState);
  private readonly formKey = 'entrada';

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

  // --- Datos recordados de una placa ya registrada ---
  // vehiculoConocido = true -> tipo/color/marca se autocompletan y quedan bloqueados.
  vehiculo = signal<VehiculoInfo | null>(null);
  vehiculoConocido = signal(false);

  // --- Estado del envío ---
  enviando = signal(false);

  // --- Ocupación actual (panel lateral informativo) ---
  ocupacion = signal<Ocupacion | null>(null);

  constructor() {
    // Llenamos el dropdown de tipos al abrir la vista.
    this.api.getTipos().subscribe({
      next: (resp) => this.tipos.set(resp.datos),
      error: (err) => { console.error(err); this.toast.error('No se pudieron cargar los tipos.'); }
    });

    this.cargarOcupacion();
    this.restaurar();   // si quedó algo escrito antes de cambiar de módulo, lo recupera
  }

  /** Restaura el formulario con lo que se guardó al salir del módulo (si hay). */
  private restaurar(): void {
    const s = this.formState.load<EstadoEntrada>(this.formKey);
    if (!s) return;
    this.placa = s.placa;
    this.idTipo = s.idTipo;
    this.idEspacio = s.idEspacio;
    this.color = s.color;
    this.marca = s.marca;
    this.esMensual.set(s.esMensual);
    this.mensual.set(s.mensual);
    this.vehiculo.set(s.vehiculo);
    this.vehiculoConocido.set(s.vehiculoConocido);
    // La lista de espacios (caso ocasional) es derivada: la recargamos.
    if (s.esMensual === false && s.idTipo !== null) this.recargarEspacios();
  }

  /** Al cambiar de módulo: guarda lo escrito para no perderlo al volver. */
  ngOnDestroy(): void {
    this.formState.save(this.formKey, {
      placa: this.placa,
      idTipo: this.idTipo,
      idEspacio: this.idEspacio,
      color: this.color,
      marca: this.marca,
      esMensual: this.esMensual(),
      mensual: this.mensual(),
      vehiculo: this.vehiculo(),
      vehiculoConocido: this.vehiculoConocido(),
    } satisfies EstadoEntrada);
  }

  /** Trae el estado de ocupación para el panel lateral. */
  private cargarOcupacion(): void {
    this.api.getOcupacion().subscribe({
      next: (resp) => this.ocupacion.set(resp),
      error: (err) => console.error(err)
    });
  }

  /**
   * Al salir del campo placa: normaliza a mayúsculas, recuerda los datos si la
   * placa ya está registrada (tipo/color/marca, bloqueados) y consulta si es mensual.
   */
  onPlacaBlur(): void {
    this.placa = this.placa.trim().toUpperCase();

    if (!this.placa) {
      this.olvidarRecordado();
      this.esMensual.set(null);
      this.mensual.set(null);
      return;
    }

    // 1) ¿La placa ya existe? -> recordamos su tipo y atributos (no editables).
    this.api.getVehiculo(this.placa).subscribe({
      next: (v) => {
        if (v.existe) {
          this.vehiculo.set(v);
          this.vehiculoConocido.set(true);
          this.idTipo = v.id_tipo;
          this.color = v.color ?? '';
          this.marca = v.marca ?? '';
        } else {
          this.olvidarRecordado();
        }
        // 2) Ya con el tipo definido, verificamos la mensualidad (cupo reservado).
        this.verificarMensualidad();
      },
      error: (err) => {
        console.error(err);
        this.olvidarRecordado();
        this.verificarMensualidad();
      }
    });
  }

  /** Olvida los datos recordados (placa nueva o vacía): los campos quedan editables. */
  private olvidarRecordado(): void {
    this.vehiculo.set(null);
    this.vehiculoConocido.set(false);
    this.idTipo = null;
    this.color = '';
    this.marca = '';
  }

  /** Consulta si la placa tiene mensualidad activa hoy (define el cupo y el modo). */
  private verificarMensualidad(): void {
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
        this.cargarOcupacion();   // el panel refleja el nuevo estado
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
    this.vehiculo.set(null);
    this.vehiculoConocido.set(false);
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
