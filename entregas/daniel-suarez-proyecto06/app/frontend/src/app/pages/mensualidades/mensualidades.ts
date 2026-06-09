import { Component, signal, inject, HostListener } from '@angular/core';
import { FormsModule } from '@angular/forms';
import {
  Api, TipoVehiculoItem, EspacioLibre, Mensualidad, MensualidadIn, VehiculoMensualIn
} from '../../services/api';
import { Toast } from '../../services/toast';

// Una fila editable de vehículo: placa + tipo + su cupo (id_espacio).
type FilaVehiculo = { placa: string; id_tipo: number | null; id_espacio: number | null };

@Component({
  selector: 'app-mensualidades',
  imports: [FormsModule],
  templateUrl: './mensualidades.html',
  styleUrl: './mensualidades.css'
})
export class MensualidadesComponent {
  private api = inject(Api);
  private toast = inject(Toast);

  // --- Lista ---
  mensualidades = signal<Mensualidad[]>([]);
  cargando = signal(true);

  // --- Catálogos ---
  tipos = signal<TipoVehiculoItem[]>([]);
  valorMesPorTipo = signal<Map<number, number>>(new Map());     // id_tipo -> valor_mes
  // Espacios LIBRES por tipo (caché): se piden la 1ª vez que se elige un tipo.
  librePorTipo = signal<Map<number, EspacioLibre[]>>(new Map());

  // --- Formulario de alta ---
  documento = '';
  nombre = '';
  telefono = '';
  email = '';
  fechaInicio = '';
  vehiculos = signal<FilaVehiculo[]>([{ placa: '', id_tipo: null, id_espacio: null }]);

  enviando = signal(false);

  // --- Modal de cancelación ---
  cancelando = signal<Mensualidad | null>(null);
  cancelandoId = signal<number | null>(null);

  // --- Modal de renovación ---
  renovando = signal<Mensualidad | null>(null);
  renovVehiculos = signal<FilaVehiculo[]>([]);
  renovandoId = signal<number | null>(null);

  constructor() {
    this.cargar();
    this.api.getTipos().subscribe({
      next: (resp) => this.tipos.set(resp.datos),
      error: (err) => console.error(err)
    });
    this.api.getTarifasMensuales().subscribe({
      next: (resp) => {
        const mapa = new Map<number, number>();
        for (const t of resp.datos) mapa.set(t.id_tipo, Number(t.valor_mes));
        this.valorMesPorTipo.set(mapa);
      },
      error: (err) => console.error(err)
    });
  }

  cargar(): void {
    this.cargando.set(true);
    this.api.getMensualidades().subscribe({
      next: (resp) => { this.mensualidades.set(resp.datos); this.cargando.set(false); },
      error: (err) => { console.error(err); this.toast.error('No se pudieron cargar las mensualidades.'); this.cargando.set(false); }
    });
  }

  /** Formatea con separador de miles (es-CO): 300000 -> "300.000". */
  fmt(n: number): string {
    return (n ?? 0).toLocaleString('es-CO');
  }

  // ===== Espacios por fila =====
  /** Carga (si falta) los espacios libres de un tipo en la caché. */
  private cargarLibresDeTipo(idTipo: number): void {
    if (this.librePorTipo().has(idTipo)) return;
    this.api.getEspaciosLibres(idTipo).subscribe({
      next: (resp) => {
        this.librePorTipo.update((m) => {
          const copia = new Map(m);
          copia.set(idTipo, resp.datos);
          return copia;
        });
      },
      error: (err) => { console.error(err); this.toast.error('No se pudieron cargar los cupos.'); }
    });
  }

  /** Al cambiar el tipo de una fila: resetea su cupo y carga los libres de ese tipo. */
  onTipoChange(fila: FilaVehiculo): void {
    fila.id_espacio = null;
    if (fila.id_tipo !== null) this.cargarLibresDeTipo(fila.id_tipo);
  }

  /** Cupos que puede elegir una fila: libres de su tipo, sin los ya elegidos en otras filas. */
  opcionesEspacio(fila: FilaVehiculo, lista: FilaVehiculo[]): EspacioLibre[] {
    if (fila.id_tipo === null) return [];
    const libres = this.librePorTipo().get(fila.id_tipo) ?? [];
    const usadosPorOtros = new Set(
      lista.filter((v) => v !== fila && v.id_espacio !== null).map((v) => v.id_espacio)
    );
    return libres.filter((e) => !usadosPorOtros.has(e.id_espacio));
  }

  // ===== Dropdown propio del cupo (el <select> nativo se desbordaba) =====
  comboAbierto = signal<string | null>(null);   // clave de la fila cuyo combo está abierto

  toggleCombo(clave: string, ev: MouseEvent): void {
    ev.stopPropagation();   // que este clic no llegue al document y lo cierre
    this.comboAbierto.update((actual) => (actual === clave ? null : clave));
  }
  elegirCupo(fila: FilaVehiculo, idEspacio: number): void {
    fila.id_espacio = idEspacio;
    this.comboAbierto.set(null);
  }
  /** Texto del botón del combo: el cupo elegido o el placeholder. */
  nombreCupo(fila: FilaVehiculo): string {
    if (fila.id_espacio === null || fila.id_tipo === null) return '— Cupo —';
    const e = (this.librePorTipo().get(fila.id_tipo) ?? []).find((x) => x.id_espacio === fila.id_espacio);
    return e ? `N° ${e.numero}` : '— Cupo —';
  }
  @HostListener('document:click')
  cerrarCombos(): void { this.comboAbierto.set(null); }
  @HostListener('document:keydown.escape')
  escCombos(): void { this.comboAbierto.set(null); }

  /** Suma del valor mensual de las filas con tipo elegido. */
  private montoDe(lista: FilaVehiculo[]): number {
    const mapa = this.valorMesPorTipo();
    return lista.reduce((s, v) => s + (v.id_tipo !== null ? (mapa.get(v.id_tipo) ?? 0) : 0), 0);
  }
  montoEstimado(): number { return this.montoDe(this.vehiculos()); }
  montoRenovacion(): number { return this.montoDe(this.renovVehiculos()); }

  /** fecha_inicio + 1 mes (preview; el backend lo recalcula). */
  fechaFinEstimada(): string {
    if (!this.fechaInicio) return '—';
    return this.masUnMes(new Date(this.fechaInicio + 'T00:00:00'));
  }
  fechaHoy(): string { return new Date().toISOString().slice(0, 10); }
  vencimientoRenovacion(): string { return this.masUnMes(new Date()); }

  private masUnMes(d: Date): string {
    const dia = d.getDate();
    d.setMonth(d.getMonth() + 1);
    if (d.getDate() !== dia) d.setDate(0);   // corrige fin de mes
    return d.toISOString().slice(0, 10);
  }

  // ===== Filas dinámicas (alta) =====
  agregarVehiculo(): void {
    this.vehiculos.update((v) => [...v, { placa: '', id_tipo: null, id_espacio: null }]);
  }
  quitarVehiculo(i: number): void {
    this.vehiculos.update((v) => v.filter((_, idx) => idx !== i));
  }

  // ===== Crear =====
  crear(): void {
    if (!this.documento.trim() || !this.nombre.trim()) {
      this.toast.error('Documento y nombre del cliente son obligatorios.'); return;
    }
    if (!this.fechaInicio) { this.toast.error('Indica la fecha de inicio.'); return; }

    const vehs = this.normalizar(this.vehiculos());
    if (vehs === null) return;

    const m: MensualidadIn = {
      cliente: {
        documento: this.documento.trim(),
        nombre_completo: this.nombre.trim(),
        telefono: this.telefono.trim() || null,
        email: this.email.trim() || null,
      },
      fecha_inicio: this.fechaInicio,
      vehiculos: vehs,
    };

    this.enviando.set(true);
    this.api.postMensualidad(m).subscribe({
      next: (resp) => {
        this.toast.exito(`Mensualidad creada (cupos N° ${resp.numeros_espacio.join(', ')}, vence ${resp.fecha_fin}, monto $${this.fmt(resp.monto)}).`);
        this.enviando.set(false);
        this.limpiar();
        this.refrescarCupos();
        this.cargar();
      },
      error: (err) => { console.error(err); this.toast.error(this.extraerError(err)); this.enviando.set(false); }
    });
  }

  /** Valida y normaliza las filas a la forma del backend. Devuelve null si hay error. */
  private normalizar(lista: FilaVehiculo[]): VehiculoMensualIn[] | null {
    if (lista.length === 0) { this.toast.error('Agrega al menos un vehículo.'); return null; }
    const vehs = lista.map((v) => ({
      placa: v.placa.trim().toUpperCase(), id_tipo: v.id_tipo, id_espacio: v.id_espacio,
    }));
    if (vehs.some((v) => !v.placa || v.id_tipo === null || v.id_espacio === null)) {
      this.toast.error('Cada vehículo necesita placa, tipo y espacio.'); return null;
    }
    const espacios = vehs.map((v) => v.id_espacio);
    if (new Set(espacios).size !== espacios.length) {
      this.toast.error('Dos vehículos no pueden usar el mismo espacio.'); return null;
    }
    return vehs as VehiculoMensualIn[];
  }

  private limpiar(): void {
    this.documento = ''; this.nombre = ''; this.telefono = ''; this.email = '';
    this.fechaInicio = '';
    this.vehiculos.set([{ placa: '', id_tipo: null, id_espacio: null }]);
  }

  /** Tras escribir en la BD, la caché de libres quedó obsoleta: la vaciamos. */
  private refrescarCupos(): void {
    this.librePorTipo.set(new Map());
  }

  // ===== Cancelación =====
  pedirCancelar(m: Mensualidad): void { this.cancelando.set(m); }
  cerrarCancelar(): void { this.cancelando.set(null); }
  confirmarCancelacion(): void {
    const m = this.cancelando();
    if (!m) return;
    this.cancelandoId.set(m.id_mensualidad);
    this.api.cancelarMensualidad(m.id_mensualidad).subscribe({
      next: () => {
        this.toast.exito(`Mensualidad de ${m.cliente} cancelada; cupos liberados.`);
        this.cancelandoId.set(null);
        this.cancelando.set(null);
        this.refrescarCupos();
        this.cargar();
      },
      error: (err) => {
        console.error(err);
        this.toast.error(this.extraerError(err));
        this.cancelandoId.set(null);
        this.cancelando.set(null);
      }
    });
  }

  // ===== Vencer expiradas =====
  vencer(): void {
    this.api.vencerExpiradas().subscribe({
      next: (resp) => {
        this.toast.exito(`Barrido completado: ${resp.mensualidades_vencidas} mensualidad(es) vencida(s).`);
        this.refrescarCupos();
        this.cargar();
      },
      error: (err) => { console.error(err); this.toast.error('No se pudo ejecutar el barrido.'); }
    });
  }

  // ===== Renovación =====
  /** True si el cliente de 'm' ya tiene una mensualidad ACTIVA (no se debe poder renovar otra). */
  clienteTieneActiva(m: Mensualidad): boolean {
    return this.mensualidades().some(
      (x) => x.id_cliente === m.id_cliente && x.estado === 'ACTIVA'
    );
  }

  pedirRenovar(m: Mensualidad): void {
    this.renovando.set(m);
    this.renovVehiculos.set([]);
    // Precargamos placa+tipo de la vencida; el espacio se elige de nuevo (los anteriores pudieron ocuparse).
    this.api.getVehiculosDeMensualidad(m.id_mensualidad).subscribe({
      next: (resp) => {
        this.renovVehiculos.set(
          resp.datos.map((v) => ({ placa: v.placa, id_tipo: v.id_tipo, id_espacio: null }))
        );
        for (const v of resp.datos) this.cargarLibresDeTipo(v.id_tipo);
      },
      error: (err) => { console.error(err); this.toast.error('No se pudieron cargar los vehículos.'); }
    });
  }
  cerrarRenovar(): void { this.renovando.set(null); }
  agregarVehRenov(): void {
    this.renovVehiculos.update((v) => [...v, { placa: '', id_tipo: null, id_espacio: null }]);
  }
  quitarVehRenov(i: number): void {
    this.renovVehiculos.update((v) => v.filter((_, idx) => idx !== i));
  }

  confirmarRenovacion(): void {
    const m = this.renovando();
    if (!m) return;
    const vehs = this.normalizar(this.renovVehiculos());
    if (vehs === null) return;

    this.renovandoId.set(m.id_mensualidad);
    this.api.renovarMensualidad(m.id_mensualidad, vehs).subscribe({
      next: (resp) => {
        this.toast.exito(`Mensualidad de ${m.cliente} renovada: nuevo período hasta ${resp.fecha_fin} (monto $${this.fmt(resp.monto)}).`);
        this.renovandoId.set(null);
        this.renovando.set(null);
        this.refrescarCupos();
        this.cargar();
      },
      error: (err) => {
        console.error(err);
        this.toast.error(this.extraerError(err));
        this.renovandoId.set(null);
        this.renovando.set(null);
      }
    });
  }

  private extraerError(err: any): string {
    const detail = err?.error?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) return detail.map((d) => d.msg).join(' · ');
    return 'Ocurrió un error.';
  }
}
