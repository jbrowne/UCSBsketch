from Observers import ArrowObserver
from Observers import CircleObserver
from Observers import DiGraphObserver
from Observers import LineObserver
from Observers import TextObserver
from Observers import TuringMachineObserver
from Observers.ChartObserver import ChartAreaCollector
from Observers.ChartObserver import ChartVisualizer
from Observers.EquationObserver import EquationCollector
from Observers.EquationObserver import EquationMarker
from Observers.EquationObserver import EquationVisualizer

def initializeBoard(board):
    """Board initialization code, conveniently placed at the beginning of the
    file for easy modification"""

    if board is not None:
        EquationCollector(board)
#        EquationVisualizer(board)
        ArrowObserver.ArrowMarker(board)
#        ArrowObserver.ArrowVisualizer(board)
        ChartAreaCollector(board)
        ChartVisualizer(board)
        """
        CircleObserver.CircleMarker(board)
        #CircleObserver.CircleVisualizer(board)
        LineObserver.LineMarker(board)
        #LineObserver.LineVisualizer(board)
        TextObserver.TextCollector(board)
        #TextObserver.TextVisualizer(board)
        DiGraphObserver.DiGraphMarker(board)
        DiGraphObserver.DiGraphVisualizer(board)
        DiGraphObserver.DiGraphExporter(board)
        TuringMachineObserver.TuringMachineCollector(board)
        TuringMachineObserver.TuringMachineExporter(board)
        TuringMachineObserver.TuringMachineVisualizer(board)
        RubineObserver.RubineMarker(board, "RubineData.xml", debug=True)
        RubineObserver.RubineVisualizer(board)

        DirectedLine.DirectedLineMarker(board)

        NumberObserver.NumCollector(board)
        NumberObserver.NumVisualizer(board)

        #BinObserver.BinCollector(board)
        #BinObserver.BinVisualizer(board)
        EqualsObserver.EqualsMarker(board)
        EqualsObserver.EqualsVisualizer(board)
        PlusObserver.PlusMarker(board)
        PlusObserver.PlusVisualizer(board)
        MinusObserver.MinusMarker(board)
        MinusObserver.MinusVisualizer(board)
        DivideObserver.DivideMarker(board)
        DivideObserver.DivideVisualizer(board)
        MultObserver.MultMarker(board)
        MultObserver.MultVisualizer(board)
        ExpressionObserver.ExpressionObserver(board)
        ExpressionObserver.ExpressionVisualizer(board)
        #EquationObserver.EquationObserver(board)
        #EquationObserver.EquationVisualizer(board)


        TestAnimObserver.TestMarker()
        TestAnimObserver.TestAnimator(fps = 1 / 3.0)
        RaceTrackObserver.SplitStrokeMarker()
        RaceTrackObserver.SplitStrokeVisualizer()
        RaceTrackObserver.RaceTrackMarker()
        RaceTrackObserver.RaceTrackVisualizer()
        TemplateObserver.TemplateMarker()
        TemplateObserver.TemplateVisualizer()
        """


        """
        d = DebugObserver.DebugObserver(board)
        d.trackAnnotation(ArrowObserver.ArrowHeadAnnotation)
        d.trackAnnotation(DiGraphObserver.DiGraphNodeAnnotation)
        d.trackAnnotation(TestAnimObserver.TestAnnotation)
        #d.trackAnnotation(MSAxesObserver.LabelMenuAnnotation)
        #d.trackAnnotation(MSAxesObserver.LegendAnnotation)
        d.trackAnnotation(LineObserver.LineAnnotation)
        d.trackAnnotation(ArrowObserver.ArrowAnnotation)
        #d.trackAnnotation(MSAxesObserver.AxesAnnotation)
        d.trackAnnotation(TemplateObserver.TemplateAnnotation)
        d.trackAnnotation(CircleObserver.CircleAnnotation)
        d.trackAnnotation(RaceTrackObserver.RaceTrackAnnotation)
        d.trackAnnotation(RaceTrackObserver.SplitStrokeAnnotation)

        d.trackAnnotation(TuringMachineObserver.TuringMachineAnnotation)
        d.trackAnnotation(DiGraphObserver.DiGraphAnnotation)
        d.trackAnnotation(TextObserver.TextAnnotation)
        #d.trackAnnotation(BarAnnotation)
        """

