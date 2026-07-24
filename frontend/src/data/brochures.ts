export interface BrochureItem {
  id: string
  ubicacion: string
  proyecto: string
  url: string
  /** Portada (primera página) del flipbook Heyzine. */
  coverImage: string
}

/** Brochures aprobados desde Links brochures.xlsx (hoja Links brochure). */
export const BROCHURES: BrochureItem[] = [
  {
    id: 'versalles',
    ubicacion: 'Ciudadela Maiporé',
    proyecto: 'Versalles',
    url: 'https://heyzine.com/flip-book/be784b0d5c.html',
    coverImage:
      'https://cdnc.heyzine.com/files/uploaded/v3/be784b0d5ce02e83deebea0cad55f3a04829ae9c.pdf-thumb.jpg',
  },
  {
    id: 'pamplona',
    ubicacion: 'Ciudadela Maiporé',
    proyecto: 'Pamplona',
    url: 'https://heyzine.com/flip-book/c159d5d733.html',
    coverImage:
      'https://cdnc.heyzine.com/files/uploaded/v3/c159d5d733b09efe543a524b50f5b60d228a9016.pdf-thumb.jpg',
  },
  {
    id: 'zarzal',
    ubicacion: 'Ciudadela Maiporé',
    proyecto: 'Zarzal',
    url: 'https://heyzine.com/flip-book/56764c1e33.html',
    coverImage:
      'https://cdnc.heyzine.com/files/uploaded/56764c1e33d876d67bcca41b3cda5414f36cb8cf-1.pdf-thumb.jpg',
  },
  {
    id: 'la-macarena',
    ubicacion: 'Ciudadela Maiporé',
    proyecto: 'La Macarena',
    url: 'https://heyzine.com/flip-book/b168b2f5ba.html',
    coverImage:
      'https://cdnc.heyzine.com/files/uploaded/b168b2f5ba52412aa3cebe352a90c6f95b73fe2c-2.pdf-thumb.jpg',
  },
  {
    id: 'mongui',
    ubicacion: 'Ciudadela Maiporé',
    proyecto: 'Monguí',
    url: 'https://heyzine.com/flip-book/866af8f6a6.html',
    coverImage:
      'https://cdnc.heyzine.com/files/uploaded/v3/866af8f6a66082c3b8f0fa2654e639bfe413e81f.pdf-thumb.jpg',
  },
  {
    id: 'bosque-arrayan',
    ubicacion: 'Tocancipá',
    proyecto: 'Bosque de Arrayán',
    url: 'https://heyzine.com/flip-book/7f3c85cf46.html',
    coverImage:
      'https://cdnc.heyzine.com/files/uploaded/7f3c85cf4681596d32975f6c19a258742bf481a6-2.pdf-thumb.jpg',
  },
  {
    id: 'bosque-turpial',
    ubicacion: 'Tocancipá',
    proyecto: 'Bosque de Turpial',
    url: 'https://heyzine.com/flip-book/5eec0a2afc.html',
    coverImage:
      'https://cdnc.heyzine.com/files/uploaded/5eec0a2afc8e6f34dac69258ab26b67724d528ee.pdf-thumb.jpg',
  },
  {
    id: 'inari',
    ubicacion: 'Chía',
    proyecto: 'Inari',
    url: 'https://heyzine.com/flip-book/8b6615372f.html',
    coverImage:
      'https://cdnc.heyzine.com/files/uploaded/v3/8b6615372fffc54771927bc8fe0151d0091d285f.pdf-thumb.jpg',
  },
  {
    id: 'reserva-aguayacan',
    ubicacion: 'Girardot',
    proyecto: 'Reserva de Aguayacán',
    url: 'https://heyzine.com/flip-book/aa430852c2.html',
    coverImage:
      'https://cdnc.heyzine.com/files/uploaded/aa430852c2281902b828c27bf027af0655989584.pdf-thumb.jpg',
  },
  {
    id: 'saman',
    ubicacion: 'Ricaurte',
    proyecto: 'Samán',
    url: 'https://heyzine.com/flip-book/1daa8c80c5.html',
    coverImage:
      'https://cdnc.heyzine.com/files/uploaded/1daa8c80c56cffb9b0cdd3882c88831412249af9-3.pdf-thumb.jpg',
  },
  {
    id: 'payande',
    ubicacion: 'Ricaurte',
    proyecto: 'Payandé',
    url: 'https://heyzine.com/flip-book/34ac4d8a9e.html',
    coverImage:
      'https://cdnc.heyzine.com/files/uploaded/v3/34ac4d8a9e7889f1c2b73272dac578569521bc24.pdf-thumb.jpg',
  },
  {
    id: 'vibo-once',
    ubicacion: 'Ricaurte',
    proyecto: 'Vibo Once',
    url: 'https://heyzine.com/flip-book/d3d1f61d6b.html',
    coverImage:
      'https://cdnc.heyzine.com/files/uploaded/v3/d3d1f61d6b986af8f5cfe8fac078aa5ea8c96a02-1.pdf-thumb.jpg',
  },
  {
    id: 'karakali',
    ubicacion: 'Ricaurte',
    proyecto: 'Karakali',
    url: 'https://heyzine.com/flip-book/5083a3d46c.html',
    coverImage:
      'https://cdnc.heyzine.com/files/uploaded/5083a3d46c423cf8924b85d5b798e728f3bb50da-4.pdf-thumb.jpg',
  },
  {
    id: 'araucaria',
    ubicacion: 'Ciudadela Calle 80',
    proyecto: 'Araucaria',
    url: 'https://heyzine.com/flip-book/26d2b013cf.html',
    coverImage:
      'https://cdnc.heyzine.com/files/uploaded/26d2b013cf7225db703c2bde5ff96c5f81fb1906-2.pdf-thumb.jpg',
  },
  {
    id: 'los-nogales',
    ubicacion: 'Ciudadela Calle 80',
    proyecto: 'Los Nogales',
    url: 'https://heyzine.com/flip-book/9dd9bf814e.html',
    coverImage:
      'https://cdnc.heyzine.com/files/uploaded/9dd9bf814e85b164faadfbd527568e36735154d7-1.pdf-thumb.jpg',
  },
  {
    id: 'verde-esperanza',
    ubicacion: 'Ubaté',
    proyecto: 'Verde Esperanza',
    url: 'https://heyzine.com/flip-book/ea1997d7ae.html',
    coverImage:
      'https://cdnc.heyzine.com/files/uploaded/v3/ea1997d7ae6f96d3124eea9a740cdd3a2ea401e2-3.pdf-thumb.jpg',
  },
  {
    id: 'multiproyecto',
    ubicacion: 'Multiproyecto',
    proyecto: 'Multiproyecto',
    url: 'https://heyzine.com/flip-book/1de36642fc.html',
    coverImage:
      'https://cdnc.heyzine.com/files/uploaded/v3/1de36642fc03010e335a632401ce2fad82df2f67-1.pdf-thumb.jpg',
  },
  {
    id: 'revista',
    ubicacion: 'Multiproyecto',
    proyecto: 'Revista',
    url: 'https://heyzine.com/flip-book/1cdf69c6d5.html',
    coverImage:
      'https://cdnc.heyzine.com/files/uploaded/1cdf69c6d5e12951de6af1a9403eccadc8e80f41-2.pdf-thumb.jpg',
  },
]
