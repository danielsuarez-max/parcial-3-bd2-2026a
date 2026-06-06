import { Component, signal, inject } from '@angular/core';
import { DatePipe } from '@angular/common';
import { Api, VehiculoDentro } from './services/api';

@Component({
  selector: 'app-root',
  imports: [DatePipe],          // DatePipe nos deja formatear fechas en la plantilla
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {
  private api = inject(Api);    // pedimos el servicio (el "mesero")

  // signals = celdas reactivas: si cambian, la pantalla se actualiza sola.
  vehiculos = signal<VehiculoDentro[]>([]);   // la lista de vehículos dentro
  cargando = signal(true);                     // ¿estamos esperando la respuesta?
  error = signal<string | null>(null);         // mensaje de error (si falla la conexión)

  constructor() {
    // Aquí nos SUSCRIBIMOS: esto dispara realmente la petición HTTP.
    this.api.getVehiculosDentro().subscribe({
      next: (resp) => {                 // llegó la respuesta OK
        this.vehiculos.set(resp.datos); // guardamos la lista en el signal
        this.cargando.set(false);
      },
      error: (err) => {                 // algo falló (backend apagado, CORS, etc.)
        console.error(err);
        this.error.set('No se pudo conectar con el backend. ¿Está corriendo en el puerto 8001?');
        this.cargando.set(false);
      }
    });
  }
}
