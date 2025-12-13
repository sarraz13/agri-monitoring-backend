import { ComponentFixture, TestBed } from '@angular/core/testing';
import { PlotDetailsComponent } from './plot-details.component';

describe('PlotDetailsComponent', () => {
  let component: PlotDetailsComponent;
  let fixture: ComponentFixture<PlotDetailsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PlotDetailsComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(PlotDetailsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});

