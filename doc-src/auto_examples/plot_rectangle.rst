

.. _sphx_glr_auto_examples_plot_rectangle.py:


rectangle
=========

Easiest way to create rectangle in svg rather than using the
:py:mod:beampy.svg.




.. code-block:: python


    from beampy import *

    # Remove quiet=True to get Beampy render outputs
    doc = document(quiet=True)

    with slide('Svg: rectangle'):
        rectangle(width=300, height=300, y='center')
        rectangle(width=100, height=100, color='yellow', y='center',
                  edgecolor='red')

    display_matplotlib(gcs())





.. image:: /auto_examples/images/sphx_glr_plot_rectangle_001.png
    :align: center




Module arguments
================

.. autoclass:: beampy.rectangle
   :noindex:





.. only :: html

 .. container:: sphx-glr-footer


  .. container:: sphx-glr-download

     :download:`Download Python source code: plot_rectangle.py <plot_rectangle.py>`



  .. container:: sphx-glr-download

     :download:`Download Jupyter notebook: plot_rectangle.ipynb <plot_rectangle.ipynb>`


.. only:: html

 .. rst-class:: sphx-glr-signature

    `Gallery generated by Sphinx-Gallery <https://sphinx-gallery.readthedocs.io>`_
